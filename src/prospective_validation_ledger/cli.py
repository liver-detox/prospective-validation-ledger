"""Command-line entry point for prospective validation bundles."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from prospective_validation_ledger import __version__
from prospective_validation_ledger.bundle import (
    StructuralError,
    _complete_draft,
    load_bundle,
)
from prospective_validation_ledger.canonical import canonical_json_bytes
from prospective_validation_ledger.verify import verify_bundle


class _UsageError(ValueError):
    """Raised for invalid command syntax without echoing supplied values."""


class _CreateError(ValueError):
    """Raised for invalid create paths without echoing supplied values."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _UsageError


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="prospective-ledger")
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("bundle", type=Path)
    verify.add_argument("--out", required=True, type=Path)
    create = commands.add_parser("create")
    create.add_argument("draft", type=Path)
    create.add_argument("--out", required=True, type=Path)
    return parser


def receipt_bytes(receipt: dict[str, Any]) -> bytes:
    return canonical_json_bytes(receipt) + b"\n"


def _atomic_write(path: Path, data: bytes) -> None:
    parent = path.parent
    if not parent.is_dir():
        raise OSError("output parent does not exist")
    descriptor, temporary_name = tempfile.mkstemp(
        dir=parent,
        prefix=f".{path.name}.",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _readable_json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)
        .encode("utf-8")
        + b"\n"
    )


def _identity(path: Path) -> tuple[int, int]:
    status = os.lstat(path)
    return status.st_dev, status.st_ino


def _clean_created_output(
    output: Path,
    output_identity: tuple[int, int],
    created_files: dict[Path, tuple[int, int]],
) -> None:
    try:
        if _identity(output) != output_identity:
            return
    except OSError:
        return

    for path, identity in created_files.items():
        try:
            if _identity(path) == identity:
                path.unlink()
        except OSError:
            pass
    try:
        if _identity(output) == output_identity:
            output.rmdir()
    except OSError:
        pass


def _create_bundle(draft: Path, output: Path) -> None:
    if not draft.is_dir():
        raise _CreateError("draft directory cannot be read")
    if os.path.lexists(output):
        raise _CreateError("output bundle already exists")
    parent = output.parent
    if not parent.is_dir():
        raise _CreateError("output parent does not exist")

    plan, snapshot, entries = _complete_draft(draft)
    outputs = {
        "plan.json": _readable_json_bytes(plan),
        "snapshot.json": _readable_json_bytes(snapshot),
        "ledger.jsonl": b"".join(
            canonical_json_bytes(entry) + b"\n" for entry in entries
        ),
    }
    temporary = Path(tempfile.mkdtemp(dir=parent, prefix=f".{output.name}."))
    output_identity: tuple[int, int] | None = None
    created_files: dict[Path, tuple[int, int]] = {}
    completed = False
    try:
        for filename, data in outputs.items():
            (temporary / filename).write_bytes(data)
        load_bundle(temporary)

        try:
            output.mkdir()
        except FileExistsError:
            raise _CreateError("output bundle already exists")
        output_identity = _identity(output)
        for filename, data in outputs.items():
            path = output / filename
            with path.open("xb") as stream:
                status = os.fstat(stream.fileno())
                created_files[path] = (status.st_dev, status.st_ino)
                stream.write(data)
        load_bundle(output)
        completed = True
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
        if output_identity is not None and not completed:
            _clean_created_output(output, output_identity, created_files)


def _error(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        arguments = parser.parse_args(argv)
    except _UsageError:
        return _error("invalid command usage")
    except SystemExit as error:
        return int(error.code)

    if arguments.command == "create":
        try:
            _create_bundle(arguments.draft, arguments.out)
        except (StructuralError, _CreateError) as error:
            return _error(str(error))
        except UnicodeEncodeError:
            return _error("invalid Unicode input")
        except OSError:
            return _error("unable to read or write requested path")
        print("created")
        return 0

    try:
        bundle_dir = arguments.bundle.resolve(strict=False)
    except RuntimeError:
        return _error("plan.json cannot be read")
    except OSError:
        return _error("unable to read or write requested path")

    try:
        inputs = tuple(
            (bundle_dir / filename).resolve(strict=False)
            for filename in ("plan.json", "snapshot.json", "ledger.jsonl")
        )
        output = arguments.out
        output_identity = output.resolve(strict=False)
    except (OSError, RuntimeError):
        return _error("unable to read or write requested path")

    if output_identity in inputs:
        return _error("output path must not replace a bundle input")

    try:
        bundle = load_bundle(bundle_dir)
    except StructuralError as error:
        return _error(str(error))
    except UnicodeEncodeError:
        return _error("invalid Unicode input")
    except OSError:
        return _error("unable to read or write requested path")

    try:
        receipt = verify_bundle(bundle, __version__)
        data = receipt_bytes(receipt)
        _atomic_write(output, data)
    except UnicodeEncodeError:
        return _error("invalid Unicode input")
    except OSError:
        return _error("unable to read or write requested path")

    status = receipt["status"]
    print(status)
    return 0 if status == "eligible" else 1
