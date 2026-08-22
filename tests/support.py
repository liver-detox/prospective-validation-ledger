from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prospective_validation_ledger.canonical import canonical_json_bytes, sha256_json


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_bundle(root: Path, entries: list[dict[str, Any]] | None = None) -> Path:
    bundle = root / "bundle"
    bundle.mkdir()
    snapshot = {
        "schema_version": "1",
        "as_of": "2026-08-15T00:00:00Z",
        "record_count": 2,
        "source_digest": "0" * 64,
    }
    plan = {
        "schema_version": "1",
        "experiment_id": "SYNTHETIC-DEMO-001",
        "rule_version": "1",
        "frozen_at": "2026-08-01T00:00:00Z",
        "as_of": snapshot["as_of"],
        "sample_ids": ["sample-A", "sample-B"],
        "snapshot_digest": sha256_json(snapshot),
    }
    rows = entries if entries is not None else [
        {
            "entry_id": "entry-001",
            "sample_id": "sample-A",
            "event_at": "2026-08-10T09:00:00Z",
            "arrived_at": "2026-08-10T09:05:00Z",
            "payload_digest": "1" * 64,
        },
        {
            "entry_id": "entry-002",
            "sample_id": "sample-B",
            "event_at": "2026-08-11T09:00:00Z",
            "arrived_at": "2026-08-11T09:05:00Z",
            "payload_digest": "2" * 64,
        },
    ]
    chained: list[dict[str, Any]] = []
    previous = "GENESIS"
    for row in rows:
        complete = {**row, "previous_entry_digest": previous}
        complete["entry_digest"] = sha256_json(complete)
        chained.append(complete)
        previous = complete["entry_digest"]
    _write_json(bundle / "plan.json", plan)
    _write_json(bundle / "snapshot.json", snapshot)
    ledger = b"".join(canonical_json_bytes(row) + b"\n" for row in chained)
    (bundle / "ledger.jsonl").write_bytes(ledger)
    return bundle
