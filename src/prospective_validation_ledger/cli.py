"""Command-line entry point for prospective validation bundles."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from prospective_validation_ledger import __version__
from prospective_validation_ledger.bundle import StructuralError, load_bundle
from prospective_validation_ledger.canonical import canonical_json_bytes
from prospective_validation_ledger.verify import verify_bundle


class _UsageError(ValueError):
    """Raised for invalid command syntax without echoing supplied values."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _UsageError


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="prospective-ledger")
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("bundle", type=Path)
    verify.add_argument("--out", required=True, type=Path)
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

    try:
        bundle_dir = arguments.bundle.resolve(strict=False)
        inputs = tuple(
            (bundle_dir / filename).resolve(strict=False)
            for filename in ("plan.json", "snapshot.json", "ledger.jsonl")
        )
        output = arguments.out.resolve(strict=False)
    except OSError:
        return _error("unable to read or write requested path")

    if output in inputs:
        return _error("output path must not replace a bundle input")

    try:
        bundle = load_bundle(bundle_dir)
    except StructuralError:
        return _error("invalid bundle structure")
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
