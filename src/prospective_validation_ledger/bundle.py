"""Strict parsing for the three files that form a validation bundle."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prospective_validation_ledger.canonical import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_json,
)


class StructuralError(ValueError):
    """Raised when one of the three bundle inputs is structurally invalid."""


@dataclass(frozen=True)
class Plan:
    raw: dict[str, Any]
    experiment_id: str
    rule_version: str
    frozen_at: datetime
    as_of: datetime
    sample_ids: tuple[str, ...]
    snapshot_digest: str


@dataclass(frozen=True)
class Snapshot:
    raw: dict[str, Any]
    as_of: datetime
    record_count: int


@dataclass(frozen=True)
class LedgerEntry:
    raw: dict[str, Any]
    line_number: int
    entry_id: str
    sample_id: str
    event_at_text: str
    arrived_at_text: str
    event_at: datetime
    arrived_at: datetime
    previous_entry_digest: str
    entry_digest: str
    computed_entry_digest: str


@dataclass(frozen=True)
class Bundle:
    plan: Plan
    snapshot: Snapshot
    entries: tuple[LedgerEntry, ...]
    plan_digest: str
    snapshot_digest: str
    ledger_digest: str


_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?"
    r"(?:Z|[+-][0-9]{2}:[0-9]{2})\Z"
)
_PLAN_FIELDS = frozenset(
    {
        "schema_version",
        "experiment_id",
        "rule_version",
        "frozen_at",
        "as_of",
        "sample_ids",
        "snapshot_digest",
    }
)
_SNAPSHOT_FIELDS = frozenset(
    {"schema_version", "as_of", "record_count", "source_digest"}
)
_SNAPSHOT_OPTIONAL_FIELDS = frozenset({"field_digest"})
_ENTRY_FIELDS = frozenset(
    {
        "entry_id",
        "sample_id",
        "event_at",
        "arrived_at",
        "previous_entry_digest",
        "entry_digest",
    }
)
_ENTRY_OPTIONAL_FIELDS = frozenset({"payload_digest"})


def load_bundle(bundle_dir: Path) -> Bundle:
    root = Path(bundle_dir)
    plan_raw = _read_json_object(root / "plan.json", "plan.json")
    snapshot_raw = _read_json_object(root / "snapshot.json", "snapshot.json")
    ledger_raw = _read_ledger(root / "ledger.jsonl")
    plan = _parse_plan(plan_raw)
    snapshot = _parse_snapshot(snapshot_raw)
    entries = tuple(_parse_entry(raw, line) for line, raw in ledger_raw)
    if plan.frozen_at > plan.as_of:
        raise StructuralError("plan.json frozen_at is later than as_of")
    if snapshot.as_of != plan.as_of:
        raise StructuralError("snapshot.json as_of does not match plan.json")
    ledger_bytes = b"".join(
        canonical_json_bytes(entry.raw) + b"\n" for entry in entries
    )
    return Bundle(
        plan=plan,
        snapshot=snapshot,
        entries=entries,
        plan_digest=sha256_json(plan_raw),
        snapshot_digest=sha256_json(snapshot_raw),
        ledger_digest=sha256_bytes(ledger_bytes),
    )


def _read_json_object(path: Path, filename: str) -> dict[str, Any]:
    return _parse_json_object(_read_utf8(path, filename), filename)


def _read_ledger(path: Path) -> list[tuple[int, dict[str, Any]]]:
    filename = "ledger.jsonl"
    text = _read_utf8(path, filename)
    rows: list[tuple[int, dict[str, Any]]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise StructuralError("ledger.jsonl has blank ledger line")
        rows.append((line_number, _parse_json_object(line, filename, line_number)))
    return rows


def _read_utf8(path: Path, filename: str) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        raise StructuralError(f"{filename} cannot be read") from None
    if data.startswith(b"\xef\xbb\xbf"):
        raise StructuralError(f"{filename} has UTF-8 byte-order mark")
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise StructuralError(f"{filename} has invalid UTF-8") from None


def _parse_json_object(
    text: str, filename: str, line_number: int | None = None
) -> dict[str, Any]:
    location = filename if line_number is None else f"{filename} line {line_number}"
    try:
        value = json.loads(
            text,
            object_pairs_hook=lambda pairs: _unique_object(pairs, location),
            parse_constant=_reject_json_constant,
        )
    except StructuralError:
        raise
    except (json.JSONDecodeError, ValueError):
        raise StructuralError(f"{location} has invalid JSON") from None
    if not isinstance(value, dict):
        raise StructuralError(f"{location} must contain a JSON object")
    return value


def _unique_object(
    pairs: list[tuple[str, Any]], location: str
) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise StructuralError(f"{location} has duplicate JSON key")
        value[key] = item
    return value


def _reject_json_constant(_: str) -> None:
    raise ValueError


def _parse_plan(raw: dict[str, Any]) -> Plan:
    filename = "plan.json"
    _validate_fields(raw, filename, _PLAN_FIELDS, frozenset())
    _validate_schema_version(raw, filename)
    experiment_id = _non_empty_string(raw, "experiment_id", filename)
    rule_version = _non_empty_string(raw, "rule_version", filename)
    frozen_at = _timestamp(raw, "frozen_at", filename)
    as_of = _timestamp(raw, "as_of", filename)
    sample_ids = _sample_ids(raw, filename)
    snapshot_digest = _digest(raw, "snapshot_digest", filename)
    return Plan(
        raw=raw,
        experiment_id=experiment_id,
        rule_version=rule_version,
        frozen_at=frozen_at,
        as_of=as_of,
        sample_ids=sample_ids,
        snapshot_digest=snapshot_digest,
    )


def _parse_snapshot(raw: dict[str, Any]) -> Snapshot:
    filename = "snapshot.json"
    _validate_fields(raw, filename, _SNAPSHOT_FIELDS, _SNAPSHOT_OPTIONAL_FIELDS)
    _validate_schema_version(raw, filename)
    as_of = _timestamp(raw, "as_of", filename)
    record_count = raw["record_count"]
    if isinstance(record_count, bool) or not isinstance(record_count, int):
        raise StructuralError("snapshot.json record_count must be an integer")
    if record_count < 0:
        raise StructuralError("snapshot.json record_count must be non-negative")
    _digest(raw, "source_digest", filename)
    if "field_digest" in raw:
        _digest(raw, "field_digest", filename)
    return Snapshot(raw=raw, as_of=as_of, record_count=record_count)


def _parse_entry(raw: dict[str, Any], line_number: int) -> LedgerEntry:
    filename = "ledger.jsonl"
    _validate_fields(raw, filename, _ENTRY_FIELDS, _ENTRY_OPTIONAL_FIELDS)
    entry_id = _non_empty_string(raw, "entry_id", filename)
    sample_id = _non_empty_string(raw, "sample_id", filename)
    event_at_text = _non_empty_string(raw, "event_at", filename)
    arrived_at_text = _non_empty_string(raw, "arrived_at", filename)
    event_at = _timestamp(raw, "event_at", filename)
    arrived_at = _timestamp(raw, "arrived_at", filename)
    if arrived_at < event_at:
        raise StructuralError("ledger.jsonl arrived_at is earlier than event_at")
    previous_entry_digest = _previous_digest(raw, filename)
    entry_digest = _digest(raw, "entry_digest", filename)
    if "payload_digest" in raw:
        _digest(raw, "payload_digest", filename)
    computed = sha256_json(
        {key: value for key, value in raw.items() if key != "entry_digest"}
    )
    return LedgerEntry(
        raw=raw,
        line_number=line_number,
        entry_id=entry_id,
        sample_id=sample_id,
        event_at_text=event_at_text,
        arrived_at_text=arrived_at_text,
        event_at=event_at,
        arrived_at=arrived_at,
        previous_entry_digest=previous_entry_digest,
        entry_digest=entry_digest,
        computed_entry_digest=computed,
    )


def _validate_fields(
    raw: dict[str, Any], filename: str, required: frozenset[str], optional: frozenset[str]
) -> None:
    unexpected = set(raw) - required - optional
    if unexpected:
        raise StructuralError(f"{filename} has unknown field")
    missing = required - set(raw)
    if missing:
        field = sorted(missing)[0]
        raise StructuralError(f"{filename} is missing {field}")


def _validate_schema_version(raw: dict[str, Any], filename: str) -> None:
    if raw["schema_version"] != "1":
        raise StructuralError(f"{filename} has unsupported schema_version")


def _non_empty_string(raw: dict[str, Any], field: str, filename: str) -> str:
    value = raw[field]
    if not isinstance(value, str) or not value:
        raise StructuralError(f"{filename} {field} must be a non-empty string")
    return value


def _timestamp(raw: dict[str, Any], field: str, filename: str) -> datetime:
    text = _non_empty_string(raw, field, filename)
    try:
        if not _TIMESTAMP.fullmatch(text):
            raise ValueError
        value = datetime.fromisoformat(text)
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise StructuralError(f"{filename} {field} must be a timestamp") from None


def _sample_ids(raw: dict[str, Any], filename: str) -> tuple[str, ...]:
    value = raw["sample_ids"]
    if not isinstance(value, list) or not value:
        raise StructuralError("plan.json sample_ids must be a non-empty list")
    if any(not isinstance(item, str) or not item for item in value):
        raise StructuralError("plan.json sample_ids must contain non-empty strings")
    if value != sorted(value):
        raise StructuralError("plan.json sample_ids must be sorted")
    if len(value) != len(set(value)):
        raise StructuralError("plan.json sample_ids must be unique")
    return tuple(value)


def _digest(raw: dict[str, Any], field: str, filename: str) -> str:
    value = raw[field]
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise StructuralError(f"{filename} {field} must be a lowercase digest")
    return value


def _previous_digest(raw: dict[str, Any], filename: str) -> str:
    value = raw["previous_entry_digest"]
    if value == "GENESIS":
        return value
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise StructuralError(
            f"{filename} previous_entry_digest must be a lowercase digest"
        )
    return value
