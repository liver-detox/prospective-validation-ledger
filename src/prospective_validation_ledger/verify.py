from __future__ import annotations

from datetime import datetime
from typing import Any

from .bundle import Bundle
from .canonical import sha256_json


def _violation(
    code: str,
    entry_index: int | None,
    sample_id: str | None,
) -> dict[str, Any]:
    return {
        "entry_index": entry_index,
        "sample_id": sample_id,
        "code": code,
    }


def _violation_key(item: dict[str, Any]) -> tuple[int, int, str, str]:
    index = item["entry_index"]
    return (
        0 if index is None else 1,
        -1 if index is None else index,
        item["code"],
        "" if item["sample_id"] is None else item["sample_id"],
    )


def verify_bundle(bundle: Bundle, tool_version: str) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    if bundle.plan.snapshot_digest != bundle.snapshot_digest:
        violations.append(_violation("DIGEST_MISMATCH", None, None))

    seen_ids: set[str] = set()
    seen_keys: set[tuple[str, datetime]] = set()
    expected_previous = "GENESIS"
    for entry in bundle.entries:
        if entry.entry_digest != entry.computed_entry_digest:
            violations.append(
                _violation("DIGEST_MISMATCH", entry.line_number, entry.sample_id)
            )
        if entry.previous_entry_digest != expected_previous:
            violations.append(
                _violation("LEDGER_GAP", entry.line_number, entry.sample_id)
            )
        if entry.entry_id in seen_ids or (
            entry.sample_id,
            entry.event_at,
        ) in seen_keys:
            violations.append(
                _violation("DUPLICATE_ENTRY", entry.line_number, entry.sample_id)
            )
        seen_ids.add(entry.entry_id)
        seen_keys.add((entry.sample_id, entry.event_at))
        if entry.sample_id not in bundle.plan.sample_ids:
            violations.append(
                _violation("UNKNOWN_SAMPLE", entry.line_number, entry.sample_id)
            )
        if entry.event_at > bundle.plan.as_of:
            violations.append(
                _violation("POST_CUTOFF_EVENT", entry.line_number, entry.sample_id)
            )
        elif entry.arrived_at > bundle.plan.as_of:
            violations.append(
                _violation("LATE_ARRIVAL", entry.line_number, entry.sample_id)
            )
        expected_previous = entry.entry_digest

    violations.sort(key=_violation_key)
    rejected_lines = {
        item["entry_index"]
        for item in violations
        if item["entry_index"] is not None
    }
    receipt: dict[str, Any] = {
        "schema_version": "1",
        "tool_version": tool_version,
        "status": "rejected" if violations else "eligible",
        "experiment_id": bundle.plan.experiment_id,
        "rule_version": bundle.plan.rule_version,
        "input_digests": {
            "plan": bundle.plan_digest,
            "snapshot": bundle.snapshot_digest,
            "ledger": bundle.ledger_digest,
        },
        "ledger_tip_digest": (
            bundle.entries[-1].entry_digest if bundle.entries else "GENESIS"
        ),
        "accepted_count": len(bundle.entries) - len(rejected_lines),
        "rejected_count": len(rejected_lines),
        "violations": violations,
    }
    receipt["receipt_digest"] = sha256_json(receipt)
    return receipt
