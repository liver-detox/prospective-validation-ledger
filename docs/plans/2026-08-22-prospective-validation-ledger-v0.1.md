# Prospective Validation Ledger v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, domain-neutral CLI that verifies a three-file
point-in-time evidence bundle and writes one deterministic eligibility
receipt.

**Architecture:** A small Python package separates deterministic JSON and
SHA-256 operations, strict bundle loading, the six audit rules, and the CLI
boundary. The verifier reads only the three named bundle files, never mutates
them, and has no network or external runtime dependency.

**Tech Stack:** Python 3.12-3.14, standard library, `unittest`, setuptools,
GitHub Actions.

**Spec:** `docs/design/2026-08-22-prospective-validation-ledger-design.md`

## Global Constraints

- Public name: **Prospective Validation Ledger**.
- Distribution name: `prospective-validation-ledger`.
- Command name: `prospective-ledger`.
- Version: `0.1.0`.
- Runtime: Python `>=3.12,<3.15`.
- Runtime dependencies: none.
- Public maintainer and copyright identity: `liver-detox`.
- License: Apache License 2.0.
- Exactly one supported workflow: `prospective-ledger verify BUNDLE --out RECEIPT`.
- Read only `plan.json`, `snapshot.json`, and `ledger.jsonl` from `BUNDLE`.
- Never recursively read the bundle, mutate inputs, access a network, inspect
  credentials, or introduce market, account, holding, order, or execution
  concepts.
- All repository fixtures are fictional and visibly marked `SYNTHETIC`.
- Implement from the public design only. Do not copy private source, tests,
  reports, data, paths, messages, configuration, or Git history.
- Git initialization, commits, remotes, pushes, and uploads require separate
  user authorization. Commit steps below are checkpoints, not current
  authorization.

---

## Planned File Map

```text
.github/workflows/ci.yml                       # read-only CI matrix
.gitignore                                     # Python/build/output ignores
DATA_POLICY.md                                 # public data and privacy boundary
LICENSE                                        # Apache License 2.0 text
README.md                                      # install, one-command use, limits
pyproject.toml                                 # package and CLI metadata
examples/SYNTHETIC_eligible/plan.json          # frozen synthetic plan
examples/SYNTHETIC_eligible/snapshot.json      # synthetic summary and digest
examples/SYNTHETIC_eligible/ledger.jsonl       # two chained synthetic entries
examples/SYNTHETIC_expected_receipt.json       # deterministic golden receipt
src/prospective_validation_ledger/__init__.py  # version only
src/prospective_validation_ledger/canonical.py # canonical JSON and SHA-256
src/prospective_validation_ledger/bundle.py    # strict input parsing and models
src/prospective_validation_ledger/verify.py    # six rules and receipt creation
src/prospective_validation_ledger/cli.py       # argparse and atomic output
tests/support.py                               # synthetic temporary-bundle builder
tests/test_canonical.py                        # canonicalization golden vectors
tests/test_bundle.py                           # structural input contract
tests/test_verify.py                           # six audit rules and determinism
tests/test_cli.py                              # end-to-end CLI and safe output
tests/test_public_boundary.py                  # small no-network/privacy check
```

The four production modules are the complete v0.1 implementation surface.
Do not add a framework, database layer, plugin abstraction, service client,
HTML renderer, public library facade, or generator command.

---

### Task 1: Package Skeleton and Canonical Digests

**Files:**

- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/prospective_validation_ledger/__init__.py`
- Create: `src/prospective_validation_ledger/canonical.py`
- Create: `tests/__init__.py`
- Create: `tests/test_canonical.py`

**Interfaces:**

- Produces: `canonical_json_bytes(value: object) -> bytes`
- Produces: `sha256_bytes(data: bytes) -> str`
- Produces: `sha256_json(value: object) -> str`
- Produces: `__version__ = "0.1.0"`

- [ ] **Step 1: Add package metadata without runtime dependencies**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[project]
name = "prospective-validation-ledger"
version = "0.1.0"
description = "Verify declared point-in-time sample eligibility and late-arrival evidence."
readme = "README.md"
requires-python = ">=3.12,<3.15"
license = "Apache-2.0"
authors = [{name = "liver-detox"}]
dependencies = []

[project.scripts]
prospective-ledger = "prospective_validation_ledger.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

Create `src/prospective_validation_ledger/__init__.py`:

```python
"""Prospective Validation Ledger."""

__version__ = "0.1.0"
```

Create the initial `README.md` required by package metadata:

```markdown
# Prospective Validation Ledger

Prospective Validation Ledger is a local command-line tool for checking
declared point-in-time sample eligibility and late-arrival evidence.

Implementation is in progress from the approved
[v0.1 design](docs/design/2026-08-22-prospective-validation-ledger-design.md).
No public release or adoption claim is made.
```

Create an empty `tests/__init__.py` so test helpers can be imported
consistently.

- [ ] **Step 2: Write the failing canonicalization tests**

Create `tests/test_canonical.py`:

```python
import unittest

from prospective_validation_ledger.canonical import (
    canonical_json_bytes,
    sha256_json,
)


class CanonicalJsonTest(unittest.TestCase):
    def test_sorted_compact_utf8_bytes_match_golden_vector(self):
        value = {"b": "雪", "a": 1}
        self.assertEqual(
            canonical_json_bytes(value),
            b'{"a":1,"b":"\xe9\x9b\xaa"}',
        )
        self.assertEqual(
            sha256_json(value),
            "f317713ac99270129844375745820bbf1f628cff9a4b11d3e67e16129ff6e0d3",
        )

    def test_non_finite_number_is_rejected(self):
        with self.assertRaises(ValueError):
            canonical_json_bytes({"value": float("nan")})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the focused test and confirm the expected failure**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_canonical -v
```

Expected: import failure because `canonical.py` does not exist.

- [ ] **Step 4: Implement the minimal canonicalization module**

Create `src/prospective_validation_ledger/canonical.py`:

```python
"""Deterministic JSON and digest operations."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))
```

- [ ] **Step 5: Run the focused test and package import check**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_canonical -v
PYTHONPATH=src python -c "from prospective_validation_ledger import __version__; assert __version__ == '0.1.0'"
```

Expected: both commands pass.

- [ ] **Step 6: Commit the independently testable canonical core**

Only after explicit local-Git authorization:

```bash
git add pyproject.toml README.md src/prospective_validation_ledger tests/__init__.py tests/test_canonical.py
git commit -m "feat: add deterministic canonical digests"
```

---

### Task 2: Strict Three-File Bundle Loader

**Files:**

- Create: `src/prospective_validation_ledger/bundle.py`
- Create: `tests/support.py`
- Create: `tests/test_bundle.py`

**Interfaces:**

- Consumes: `canonical_json_bytes`, `sha256_bytes`, `sha256_json`
- Produces: `StructuralError(ValueError)` with controlled, non-sensitive text
- Produces: top-level frozen internal `Plan`, `Snapshot`, `LedgerEntry`, and
  `Bundle` dataclasses; contained raw dictionaries are not a public immutability
  guarantee
- Produces: `load_bundle(bundle_dir: Path) -> Bundle`

- [ ] **Step 1: Add a reusable synthetic-bundle builder for tests**

Create `tests/support.py` with one public helper:

```python
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
```

The helper creates only fictional values. Later tests may load and rewrite
these dictionaries to create one focused violation at a time.

- [ ] **Step 2: Write failing loader tests for valid and malformed bundles**

Create `tests/test_bundle.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from prospective_validation_ledger.bundle import StructuralError, load_bundle
from tests.support import write_bundle


class BundleLoaderTest(unittest.TestCase):
    def test_valid_bundle_loads_three_inputs_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            (bundle_dir / "ignored.txt").write_text("not read", encoding="utf-8")
            bundle = load_bundle(bundle_dir)
            self.assertEqual(bundle.plan.experiment_id, "SYNTHETIC-DEMO-001")
            self.assertEqual(len(bundle.entries), 2)
            self.assertEqual(bundle.entries[0].line_number, 1)

    def test_duplicate_json_key_is_structurally_invalid(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            (bundle_dir / "plan.json").write_text(
                '{"schema_version":"1","schema_version":"1"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(StructuralError, "duplicate JSON key"):
                load_bundle(bundle_dir)

    def test_naive_timestamp_is_structurally_invalid(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            path = bundle_dir / "plan.json"
            plan = json.loads(path.read_text(encoding="utf-8"))
            plan["as_of"] = "2026-08-15T00:00:00"
            path.write_text(json.dumps(plan) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(StructuralError, "timezone"):
                load_bundle(bundle_dir)

    def test_blank_ledger_line_is_structurally_invalid(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = write_bundle(Path(temporary))
            path = bundle_dir / "ledger.jsonl"
            path.write_bytes(path.read_bytes() + b"\n")
            with self.assertRaisesRegex(StructuralError, "blank ledger line"):
                load_bundle(bundle_dir)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the loader tests and confirm the expected failure**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_bundle -v
```

Expected: import failure because `bundle.py` does not exist.

- [ ] **Step 4: Implement strict parsing and immutable internal models**

Create `src/prospective_validation_ledger/bundle.py` with these exact internal
types. They are implementation boundaries, not a stable public Python API:

```python
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
```

Implement `load_bundle()` using direct paths only:

```python
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
```

The private parsing functions must enforce the spec exactly:

- strict UTF-8 without BOM;
- JSON objects only and duplicate-key rejection through `object_pairs_hook`;
- exact required/optional field sets;
- `schema_version == "1"`;
- non-empty strings and lowercase 64-character hexadecimal digests;
- sorted, unique, non-empty `sample_ids`;
- non-Boolean, non-negative integer `record_count`;
- timezone-aware timestamps normalized to UTC for comparison;
- `arrived_at >= event_at`;
- optional `payload_digest` may be absent but never `null`;
- first-class line numbers, exact timestamp text, and computed entry digests;
- an empty ledger is allowed, while a blank physical line is not.

Use controlled `StructuralError` messages that name only the public filename
and field; never include file contents or user-supplied values.

- [ ] **Step 5: Expand the table of structural tests**

Add `subTest` cases to `tests/test_bundle.py` for all of the following, with
each case asserting `StructuralError`:

```python
cases = (
    "missing required file",
    "UTF-8 byte-order mark",
    "invalid UTF-8 bytes",
    "truncated or syntactically invalid JSON object",
    "invalid JSON on one JSONL line",
    "non-object plan or snapshot",
    "unknown field",
    "unsupported schema version",
    "unsorted sample IDs",
    "duplicate sample IDs",
    "Boolean record_count",
    "invalid digest text",
    "payload_digest set to null",
    "arrival earlier than event",
)
```

Implement each case as a concrete mutation of the bundle made by
`write_bundle`; assert `StructuralError` and confirm its controlled message
does not contain the injected invalid input text. Add positive cases proving a
missing `payload_digest` loads successfully and a valid `field_digest` loads
successfully; also prove an invalid `field_digest` is rejected.

- [ ] **Step 6: Run the loader and canonicalization suites**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_canonical tests.test_bundle -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit the strict bundle contract**

Only after explicit local-Git authorization:

```bash
git add src/prospective_validation_ledger/bundle.py tests/support.py tests/test_bundle.py
git commit -m "feat: load strict point-in-time bundles"
```

---

### Task 3: Six Audit Rules and Deterministic Receipt

**Files:**

- Create: `src/prospective_validation_ledger/verify.py`
- Create: `tests/test_verify.py`

**Interfaces:**

- Consumes: `Bundle` and its precomputed canonical digests
- Produces: `verify_bundle(bundle: Bundle, tool_version: str) -> dict[str, Any]`
- Produces violation objects containing only `entry_index`, `sample_id`, and
  `code`
- Produces a complete receipt dictionary including `receipt_digest`

- [ ] **Step 1: Write the eligible golden-receipt test**

Create `tests/test_verify.py` with this first test:

```python
import tempfile
import unittest
from pathlib import Path

from prospective_validation_ledger.bundle import load_bundle
from prospective_validation_ledger.verify import verify_bundle
from tests.support import write_bundle


class VerifyBundleTest(unittest.TestCase):
    def test_valid_bundle_has_deterministic_eligible_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = load_bundle(write_bundle(Path(temporary)))
            first = verify_bundle(bundle, "0.1.0")
            second = verify_bundle(bundle, "0.1.0")
            self.assertEqual(first, second)
            self.assertEqual(first["status"], "eligible")
            self.assertEqual(first["accepted_count"], 2)
            self.assertEqual(first["rejected_count"], 0)
            self.assertEqual(first["violations"], [])
            self.assertEqual(
                first["receipt_digest"],
                "14e00f8a5e683c3e87965b02069fb5c81243576ba66b32a500f6825b6aa4964e",
            )
```

- [ ] **Step 2: Run the focused test and confirm the expected failure**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_verify.VerifyBundleTest.test_valid_bundle_has_deterministic_eligible_receipt -v
```

Expected: import failure because `verify.py` does not exist.

- [ ] **Step 3: Implement the receipt builder and eligible path**

Create `src/prospective_validation_ledger/verify.py`. Keep violations as plain
dictionaries; no framework or public model layer is needed.

```python
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
```

- [ ] **Step 4: Run the eligible test and verify the golden digest**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_verify.VerifyBundleTest.test_valid_bundle_has_deterministic_eligible_receipt -v
```

Expected: pass with receipt digest
`14e00f8a5e683c3e87965b02069fb5c81243576ba66b32a500f6825b6aa4964e`.

- [ ] **Step 5: Write one focused test for every rejection code**

Extend `tests/test_verify.py`. Each test must use a fresh temporary bundle and
assert only the intended code:

```python
def assert_codes(self, receipt, expected):
    self.assertEqual(receipt["status"], "rejected")
    self.assertEqual(
        [item["code"] for item in receipt["violations"]],
        expected,
    )
```

Create these concrete cases:

```text
LATE_ARRIVAL       event 2026-08-10, arrival 2026-08-16
POST_CUTOFF_EVENT  event and arrival 2026-08-16
UNKNOWN_SAMPLE     sample-Z with otherwise valid timing
DUPLICATE_ENTRY    a third entry repeats entry-002's logical key
DIGEST_MISMATCH    change entry-001 payload after its digest is calculated
LEDGER_GAP         give entry-002 an all-zero previous digest and recalculate entry-002
```

For the last two cases, modify `ledger.jsonl` after `write_bundle()` so the
test controls whether the entry digest itself remains correct. Assert the
documented one-based `entry_index`, and assert a global snapshot mismatch uses
`null` equivalents (`None`) for index and sample ID.

Add a duplicate-key test whose two event strings represent the same UTC
instant (`2026-08-10T09:00:00Z` and `2026-08-10T17:00:00+08:00`). It must
produce `DUPLICATE_ENTRY`; the original strings remain distinct only for
digest calculation. Add a separate mutation that changes only a declared
`entry_digest` and assert `DIGEST_MISMATCH` on that line plus any resulting
`LEDGER_GAP` on the following line.

- [ ] **Step 6: Add aggregation and determinism edge tests**

Add tests that prove:

```text
- one entry may carry multiple sorted codes;
- the first duplicate remains accepted and later duplicates are rejected;
- a global snapshot mismatch rejects the bundle without changing entry counts;
- an empty ledger is eligible with GENESIS and zero counts;
- changing tool_version changes receipt_digest;
- no violation contains payload_digest, event_at, or arrived_at.
```

- [ ] **Step 7: Run the complete verifier suite**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_verify -v
```

Expected: all verifier tests pass.

- [ ] **Step 8: Commit the complete audit engine**

Only after explicit local-Git authorization:

```bash
git add src/prospective_validation_ledger/verify.py tests/test_verify.py
git commit -m "feat: verify six point-in-time audit rules"
```

---

### Task 4: One-Command CLI and Safe Receipt Writing

**Files:**

- Create: `src/prospective_validation_ledger/cli.py`
- Create: `tests/test_cli.py`

**Interfaces:**

- Consumes: `load_bundle()`, `verify_bundle()`, and `__version__`
- Produces: `main(argv: list[str] | None = None) -> int`
- Produces: installed command `prospective-ledger`
- Writes: one UTF-8 canonical receipt plus a final newline

- [ ] **Step 1: Write failing end-to-end CLI tests**

Create `tests/test_cli.py` with the essential paths:

```python
import json
import tempfile
import unittest
from pathlib import Path

from prospective_validation_ledger.cli import main
from tests.support import write_bundle


class CliTest(unittest.TestCase):
    def test_eligible_bundle_writes_one_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            output = root / "receipt.json"
            self.assertEqual(main(["verify", str(bundle), "--out", str(output)]), 0)
            receipt = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "eligible")
            self.assertTrue(output.read_bytes().endswith(b"\n"))

    def test_structural_error_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            (bundle / "plan.json").write_text("not json", encoding="utf-8")
            output = root / "receipt.json"
            output.write_bytes(b"existing\n")
            self.assertNotEqual(
                main(["verify", str(bundle), "--out", str(output)]),
                0,
            )
            self.assertEqual(output.read_bytes(), b"existing\n")

    def test_output_cannot_replace_an_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = write_bundle(root)
            plan = bundle / "plan.json"
            original = plan.read_bytes()
            self.assertNotEqual(
                main(["verify", str(bundle), "--out", str(plan)]),
                0,
            )
            self.assertEqual(plan.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the CLI tests and confirm the expected failure**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_cli -v
```

Expected: import failure because `cli.py` does not exist.

- [ ] **Step 3: Implement argument parsing and atomic output**

Create `src/prospective_validation_ledger/cli.py` around these functions:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prospective-ledger")
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
```

Implement `main()` with this exact sequence:

```text
1. Parse arguments.
2. Resolve the three input paths and output path without requiring existence.
3. Reject output equality with any input path.
4. Load the bundle; controlled StructuralError prints `error: <controlled message>`.
5. Verify and serialize the receipt fully in memory.
6. Atomically replace only the requested output.
7. Print `eligible` or `rejected` and return 0 or non-zero respectively.
8. Controlled filesystem failures print `error: unable to read or write requested path`.
```

Do not print exception representations, file contents, environment values, or
tracebacks for expected user errors.

- [ ] **Step 4: Add rejected-receipt and filesystem failure tests**

Extend `tests/test_cli.py` to prove:

```text
- an audit violation writes a rejected receipt and returns non-zero;
- a missing output parent writes nothing;
- an output path that is a directory fails without deleting it;
- deterministic reruns produce identical bytes;
- stdout contains only eligible or rejected;
- stderr never contains a synthetic payload digest or arbitrary input text.
```

- [ ] **Step 5: Run all local tests and an editable-install smoke test**

Run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m pip install -e .
prospective-ledger --help
```

Expected: tests pass, installation has no runtime dependency, and help lists
only the `verify` subcommand.

- [ ] **Step 6: Commit the one-command product surface**

Only after explicit local-Git authorization:

```bash
git add src/prospective_validation_ledger/cli.py tests/test_cli.py
git commit -m "feat: add local verification command"
```

---

### Task 5: Synthetic Example, Public Boundary, Documentation, and CI

**Files:**

- Create: `examples/SYNTHETIC_eligible/plan.json`
- Create: `examples/SYNTHETIC_eligible/snapshot.json`
- Create: `examples/SYNTHETIC_eligible/ledger.jsonl`
- Create: `examples/SYNTHETIC_expected_receipt.json`
- Create: `tests/test_public_boundary.py`
- Modify: `README.md`
- Create: `DATA_POLICY.md`
- Create: `LICENSE`
- Create: `.gitignore`
- Create: `.github/workflows/ci.yml`

**Interfaces:**

- Consumes: the installed `prospective-ledger` command
- Produces: one reproducible, entirely synthetic demonstration
- Produces: release-facing limitations and data policy
- Produces: CI for Python 3.12, 3.13, and 3.14

- [ ] **Step 1: Add the exact synthetic eligible bundle**

Create `examples/SYNTHETIC_eligible/plan.json`:

```json
{
  "schema_version": "1",
  "experiment_id": "SYNTHETIC-DEMO-001",
  "rule_version": "1",
  "frozen_at": "2026-08-01T00:00:00Z",
  "as_of": "2026-08-15T00:00:00Z",
  "sample_ids": [
    "sample-A",
    "sample-B"
  ],
  "snapshot_digest": "5f015e2aafd94d2f2e6525f245a45bb2fa68019996ab7d3143cd48b59e420edf"
}
```

Create `examples/SYNTHETIC_eligible/snapshot.json`:

```json
{
  "schema_version": "1",
  "as_of": "2026-08-15T00:00:00Z",
  "record_count": 2,
  "source_digest": "0000000000000000000000000000000000000000000000000000000000000000"
}
```

Create `examples/SYNTHETIC_eligible/ledger.jsonl` as exactly two compact lines:

```jsonl
{"entry_id":"entry-001","sample_id":"sample-A","event_at":"2026-08-10T09:00:00Z","arrived_at":"2026-08-10T09:05:00Z","payload_digest":"1111111111111111111111111111111111111111111111111111111111111111","previous_entry_digest":"GENESIS","entry_digest":"b427efca9957038edbad4b33fbb24296903fd4c80c34009400ad8f1ff03f43e8"}
{"entry_id":"entry-002","sample_id":"sample-B","event_at":"2026-08-11T09:00:00Z","arrived_at":"2026-08-11T09:05:00Z","payload_digest":"2222222222222222222222222222222222222222222222222222222222222222","previous_entry_digest":"b427efca9957038edbad4b33fbb24296903fd4c80c34009400ad8f1ff03f43e8","entry_digest":"57fe707aee812f943b9c4e76ac2428cef9af50d37e4bf98938fee92a783d0980"}
```

Every example identifier and digest pattern is fictional. Do not replace the
example with a real domain, asset, account, person, customer, provider, or
research result.

- [ ] **Step 2: Add the exact deterministic expected receipt**

Create `examples/SYNTHETIC_expected_receipt.json`:

```json
{"accepted_count":2,"experiment_id":"SYNTHETIC-DEMO-001","input_digests":{"ledger":"e77e4cb5149c9b073301a51e1be99a75169fd82c6efee9d5752a4702f92fbd02","plan":"53da8f01bb151a2001e5fe81d95d654e8b9781cb2816b1ba56bc4a7ffb557b3c","snapshot":"5f015e2aafd94d2f2e6525f245a45bb2fa68019996ab7d3143cd48b59e420edf"},"ledger_tip_digest":"57fe707aee812f943b9c4e76ac2428cef9af50d37e4bf98938fee92a783d0980","receipt_digest":"14e00f8a5e683c3e87965b02069fb5c81243576ba66b32a500f6825b6aa4964e","rejected_count":0,"rule_version":"1","schema_version":"1","status":"eligible","tool_version":"0.1.0","violations":[]}
```

The file must contain the compact object above plus one final newline.

- [ ] **Step 3: Write a small public-boundary regression test**

Create `tests/test_public_boundary.py`. It performs only two checks:

```python
import ast
import unittest
from pathlib import Path


class PublicBoundaryTest(unittest.TestCase):
    def test_source_has_no_network_or_process_imports(self):
        blocked = {"http", "requests", "httpx", "socket", "subprocess"}
        source = Path(__file__).parents[1] / "src"
        found = set()
        for path in source.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    found.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    found.add(node.module.split(".")[0])
        self.assertEqual(found & blocked, set())

    def test_examples_are_visibly_synthetic_and_have_no_private_path(self):
        root = Path(__file__).parents[1]
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (root / "examples").rglob("*")
            if path.is_file()
        )
        self.assertIn("SYNTHETIC", text)
        self.assertNotIn("/Users/", text)


if __name__ == "__main__":
    unittest.main()
```

Do not grow this into a policy engine or broad keyword blacklist.
This regression test is not a complete privacy proof; the final per-file
whitelist review remains the release gate.

- [ ] **Step 4: Write the public README and data policy**

Replace the initial `README.md` with the complete public document containing
these sections, in this order:

```text
1. One-sentence purpose
2. What it verifies
3. What it does not prove
4. Installation from a local GitHub checkout
5. One-command synthetic quick start
6. Three input files
7. eligible and rejected receipts
8. Six violation codes
9. Privacy and synthetic-data policy
10. Development and test command
11. License
```

The quick start is exactly:

```bash
python -m pip install .
prospective-ledger verify examples/SYNTHETIC_eligible --out receipt.json
```

README language must say the tool checks declared timing and internal bundle
consistency. It must explicitly deny trusted timestamping, absolute tamper
prevention, source-truth verification, model validation, prediction quality,
investment analysis, adoption, and external validation.

`DATA_POLICY.md` must state:

```text
- The repository contains synthetic fixtures only.
- The tool does not require or upload payload content.
- Users should choose pseudonymous sample IDs because rejected receipts expose IDs.
- No network, provider, account, holding, order, or execution adapter is included.
- Real or licensed datasets must not be committed to this repository.
```

- [ ] **Step 5: Add license, ignores, and read-only CI**

Create `LICENSE` from the unmodified Apache License 2.0 text. Create
`.gitignore` with only:

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
.venv/
build/
dist/
receipt.json
```

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.12", "3.13", "3.14"]
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
      - run: python -m pip install -e .
      - run: python -m unittest discover -s tests -v
      - run: prospective-ledger verify examples/SYNTHETIC_eligible --out "$RUNNER_TEMP/receipt.json"
      - run: cmp examples/SYNTHETIC_expected_receipt.json "$RUNNER_TEMP/receipt.json"
```

- [ ] **Step 6: Run full release-candidate verification**

Run from a fresh isolated environment:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
prospective-ledger verify examples/SYNTHETIC_eligible --out receipt.json
cmp examples/SYNTHETIC_expected_receipt.json receipt.json
git diff --check
```

Expected:

```text
- every test passes;
- CLI prints eligible;
- generated receipt matches the golden file byte-for-byte;
- no whitespace errors;
- inputs remain unchanged;
- only receipt.json is newly generated and ignored.
```

Then perform a whitelist review of every prospective tracked file. Confirm no
private path, non-synthetic data, credential, network endpoint, account,
holding, trade, provider payload, or copied private history is present.

- [ ] **Step 7: Commit the public release surface**

Only after explicit local-Git authorization:

```bash
git add .github .gitignore DATA_POLICY.md LICENSE README.md examples tests/test_public_boundary.py
git commit -m "docs: add synthetic release surface"
```

- [ ] **Step 8: Stop at the local release-candidate gate**

Report local test counts, exact HEAD commit, whitelist results, and remaining
facts that are still only plans. Do not create a remote repository, push,
upload, create a GitHub Release, publish to PyPI, or claim adoption without a
new explicit authorization.

---

## Execution Order and Review Gates

1. Task 1 establishes deterministic digest primitives.
2. Task 2 establishes strict, privacy-safe input parsing.
3. Task 3 implements the complete six-rule product value.
4. Task 4 exposes the one supported command without expanding scope.
5. Task 5 prepares a synthetic, locally verified release candidate.

After every task, a reviewer checks spec compliance and code quality before
the next task begins. After Task 5, run the full suite and privacy whitelist
again. The implementation is not publicly released until the user separately
authorizes GitHub creation and upload.
