# Prospective Validation Ledger v0.1 Design

- Status: design approved; implementation has not started
- Date: 2026-08-22
- Intended public maintainer: `liver-detox`
- Intended license: Apache License 2.0
- Intended first release: GitHub repository and GitHub Release only

## 1. Product decision

Prospective Validation Ledger is a local command-line tool for time-series
research. It checks whether a validation bundle is internally consistent with
its declared frozen sample set and point-in-time cutoff, and whether
late-arriving records were backfilled into that validation.

The v0.1 public contract is one workflow:

```text
prospective-ledger verify BUNDLE --out RECEIPT
```

The tool reads three input files, never modifies them, and produces one
deterministic JSON receipt. It is domain-neutral: synthetic examples use
fictional research samples rather than market, medical, customer, or other
real-world data.

The tool verifies declared timing and internal evidence consistency. A
`frozen_at` value is a self-declared part of the bundle: the tool checks its
format and ordering but does not independently prove when the plan was
created. It does not establish a trusted timestamp, prove that a source
statement is true, prevent a fully privileged local user from rebuilding a
bundle, or assess the quality of a model or research conclusion.

## 2. v0.1 scope

### Included

- A single local `verify` command.
- Structural validation of `plan.json`, `snapshot.json`, and `ledger.jsonl`.
- Frozen-sample membership and point-in-time eligibility checks.
- SHA-256 digest and ledger-chain consistency checks.
- An `eligible` or `rejected` deterministic receipt.
- Fully synthetic examples and automated tests.
- Clear limitations and privacy guidance.

### Excluded

- Network access, remote services, databases, or background processes.
- Web interfaces, dashboards, plugins, rule languages, or approval workflows.
- Digital signatures, key management, trusted timestamping, or secure custody.
- Market calendars, data-provider adapters, accounts, holdings, orders, or
  execution features.
- Model scoring, prediction evaluation, investment analysis, or return claims.
- A stable public Python API; v0.1 supports the command-line workflow only.
- PyPI publication, a project website, or hosted documentation.

## 3. Bundle contract

The bundle is a directory containing the following required inputs:

```text
bundle/
  plan.json
  snapshot.json
  ledger.jsonl
```

Unknown files in the directory are ignored. The verifier never recursively
reads subdirectories.

### 3.1 `plan.json`

Required fields:

```json
{
  "schema_version": "1",
  "experiment_id": "SYNTHETIC-DEMO-001",
  "rule_version": "1",
  "frozen_at": "2026-08-01T00:00:00Z",
  "as_of": "2026-08-15T00:00:00Z",
  "sample_ids": ["sample-A", "sample-B"],
  "snapshot_digest": "<64 lowercase hexadecimal characters>"
}
```

Rules:

- No unknown or missing fields are accepted in v0.1.
- `experiment_id`, `rule_version`, and each sample ID are non-empty UTF-8
  strings.
- `sample_ids` is non-empty, unique, and lexicographically sorted. The tool
  rejects rather than silently reorders or deduplicates it.
- `frozen_at` and `as_of` are timezone-aware ISO 8601 timestamps.
- `frozen_at` must not be later than `as_of`.
- `snapshot_digest` is the SHA-256 digest of the canonical `snapshot.json`
  object.

### 3.2 `snapshot.json`

Required fields and one optional field:

```json
{
  "schema_version": "1",
  "as_of": "2026-08-15T00:00:00Z",
  "record_count": 2,
  "source_digest": "<64 lowercase hexadecimal characters>",
  "field_digest": "<optional 64 lowercase hexadecimal characters>"
}
```

Rules:

- No fields other than the five shown above are accepted.
- `as_of` must equal `plan.json.as_of` after UTC normalization.
- `record_count` is a non-negative integer and must not be a Boolean.
- Digest fields contain lowercase SHA-256 hexadecimal text.
- The snapshot contains summaries and digests only, never business records.

`record_count` is a declared source summary. v0.1 does not equate it with the
size of `sample_ids` or the number of ledger entries and does not cross-check
those counts.

`source_digest` and optional `field_digest` are declared evidence anchors. The
verifier checks their format and covers them through the snapshot input digest,
but does not echo them separately in the receipt and cannot prove the truth or
provenance of material that is not part of the bundle.

### 3.3 `ledger.jsonl`

Each non-empty line is one JSON object with these fields:

```json
{
  "entry_id": "entry-001",
  "sample_id": "sample-A",
  "event_at": "2026-08-10T09:00:00Z",
  "arrived_at": "2026-08-10T09:05:00Z",
  "payload_digest": "<optional 64 lowercase hexadecimal characters>",
  "previous_entry_digest": "GENESIS",
  "entry_digest": "<64 lowercase hexadecimal characters>"
}
```

Rules:

- No fields other than the seven shown above are accepted.
- `entry_id`, `sample_id`, `event_at`, `arrived_at`,
  `previous_entry_digest`, and `entry_digest` are JSON strings and are
  required. `entry_id` and `sample_id` are non-empty.
- `payload_digest` may be omitted. If present, it is a JSON string containing
  64 lowercase hexadecimal characters; JSON `null` is not accepted.
- `previous_entry_digest` is `GENESIS` or 64 lowercase hexadecimal
  characters. `entry_digest` is 64 lowercase hexadecimal characters.
- The logical key is `(sample_id, event_at)`; duplicates are audited under
  `DUPLICATE_ENTRY` rather than treated as a structural parsing failure.
- Timestamps are timezone-aware ISO 8601 values.
- The first `previous_entry_digest` is `GENESIS`; every later value equals the
  preceding line's `entry_digest`.
- `entry_digest` is SHA-256 over the canonical entry without the
  `entry_digest` field.
- An empty ledger is structurally valid and produces counts of zero.

The chain is tamper-evident only in the limited sense described in this
design. Someone able to replace every local file and recompute every digest
can construct a new internally consistent bundle.

## 4. Canonicalization and time handling

- Files are UTF-8 and must not contain a byte-order mark.
- JSON objects reject duplicate keys.
- Canonical JSON uses Python's standard JSON encoder with sorted object keys,
  compact `,` and `:` separators, UTF-8 output, `ensure_ascii=False`, and
  `allow_nan=False`.
- No Unicode normalization is applied; exact decoded Unicode code points are
  significant.
- Arrays preserve their declared order.
- Timestamps must include `Z` or a numeric UTC offset and are normalized to
  UTC for comparison.
- Digest calculation preserves the exact validated timestamp strings; UTC
  normalization is used for comparison only. Equivalent timestamps written
  with different offsets therefore have different digests.
- Naive timestamps, non-finite numbers, floating-point fields, and Boolean
  substitutes for integers are rejected.
- An empty ledger file is valid. A non-empty ledger rejects blank or
  whitespace-only lines rather than silently skipping them.
- All generated JSON ends with one newline.

The implementation will freeze exact canonicalization examples in automated
tests. v0.1 does not claim a language-neutral canonical JSON standard.

## 5. Verification semantics

Structurally invalid input causes a concise command-line error, a non-zero
exit, and no receipt. Structural failures include missing or unreadable files,
invalid UTF-8 or JSON, unsupported schema versions, invalid timestamps, and
missing, unknown, or wrongly typed fields.

Structurally valid input is audited using exactly six v0.1 violation codes:

| Code | Condition |
|---|---|
| `LATE_ARRIVAL` | `event_at <= as_of` and `arrived_at > as_of` |
| `POST_CUTOFF_EVENT` | `event_at > as_of` |
| `UNKNOWN_SAMPLE` | `sample_id` is not in the frozen `sample_ids` |
| `DUPLICATE_ENTRY` | `entry_id` or `(sample_id, event_at)` is repeated |
| `DIGEST_MISMATCH` | The snapshot or an entry does not match its declared digest |
| `LEDGER_GAP` | The first link is not `GENESIS` or a later link does not match |

Any violation rejects the whole bundle. The verifier reports every violation
it can determine safely from structurally valid input; it never repairs,
overwrites, drops, or backfills a record.

Violation attachment is deterministic:

- A snapshot `DIGEST_MISMATCH` is global. An entry `DIGEST_MISMATCH` and a
  `LEDGER_GAP` attach to the offending ledger line.
- For duplicate `entry_id` or logical keys, the first occurrence remains
  unmarked and every later occurrence receives `DUPLICATE_ENTRY`.
- Ledger entry indexes are one-based physical line numbers.

An entry with `arrived_at < event_at` is structurally invalid because an
arrival cannot precede its declared event. This does not introduce a seventh
audit code.

## 6. Receipt contract

For structurally valid input, `receipt.json` contains:

```json
{
  "schema_version": "1",
  "tool_version": "0.1.0",
  "status": "eligible",
  "experiment_id": "SYNTHETIC-DEMO-001",
  "rule_version": "1",
  "input_digests": {
    "plan": "<sha256>",
    "snapshot": "<sha256>",
    "ledger": "<sha256>"
  },
  "ledger_tip_digest": "<sha256 or GENESIS>",
  "accepted_count": 2,
  "rejected_count": 0,
  "violations": [],
  "receipt_digest": "<sha256>"
}
```

Receipt rules:

- `status` is `eligible` only when there are no violations; otherwise it is
  `rejected`.
- Violations contain only `entry_index`, `sample_id`, and `code`. They do not
  echo payloads or other business values.
- Global violations use JSON `null` for `entry_index` and `sample_id`.
- Global violations are listed first. Entry-scoped violations follow by
  one-based line number, then code, then sample ID.
- `rejected_count` is the number of distinct ledger entries with entry-scoped
  violations; `accepted_count` is the remaining ledger-entry count. A global
  violation can reject the bundle without changing those two counts.
- `ledger_tip_digest` is the final line's declared `entry_digest`, even when
  the bundle is rejected; it is `GENESIS` for an empty ledger. The field is an
  identifier, not an assertion that the declared tip was valid.
- `receipt_digest` is SHA-256 over the canonical receipt without the
  `receipt_digest` field.
- Runtime timestamps are omitted. The same canonical inputs and tool version
  therefore produce byte-for-byte identical receipts.
- The output parent directory must already exist. The command writes through
  a temporary sibling and atomically replaces only the requested output file.
- The command never deletes unrelated files and refuses an output path that
  resolves to an input file.

An eligible receipt exits successfully. Structural errors and rejected
receipts exit non-zero; v0.1 does not promise a larger numeric exit-code
taxonomy.

## 7. Implementation shape

The implementation remains a small, standard-library-first Python package:

- CLI boundary: argument handling and safe receipt writing.
- Input boundary: strict UTF-8, JSON, JSONL, schema, and timestamp parsing.
- Canonicalization boundary: deterministic JSON and SHA-256 operations.
- Verification boundary: the six audit rules and aggregate status.
- Receipt boundary: deterministic, privacy-minimized output.

These are logical responsibilities, not a requirement to create a framework
or one file per concept. No runtime dependency is added unless the standard
library proves insufficient for a confirmed v0.1 requirement.

## 8. Privacy and clean-room boundary

- The public implementation is written from this independent specification.
- No private source file, test, report, dataset, path, configuration, error
  message, or Git history is copied into the project.
- Repository fixtures use fictional identifiers, dates, and values and are
  visibly marked `SYNTHETIC`.
- The program contains no networking code, URL defaults, credential readers,
  account concepts, market adapters, or execution permissions.
- The tool does not require payloads. Users should use pseudonymous sample IDs
  because sample IDs appear in rejected receipts.
- A release whitelist admits only reviewed source, tests, documentation,
  synthetic fixtures, packaging metadata, license, and CI files.

## 9. Test and acceptance contract

v0.1 is ready for public release only when all of the following are true:

1. A synthetic eligible bundle produces a receipt with one command.
2. Each of the six violation codes has a focused automated test.
3. Missing files, malformed UTF-8 or JSON, duplicate JSON keys, invalid or
   naive timestamps, unknown fields, and unsupported schemas fail safely.
4. Editing the snapshot, an entry body, an entry digest, or a chain link is
   detected as a structural or audit failure as specified above.
5. Repeating the same run produces a byte-for-byte identical receipt.
6. The verifier leaves all input bytes unchanged and never reads an unknown
   file or subdirectory.
7. CLI failure does not partially overwrite an existing receipt.
8. All fixtures are synthetic and contain no private path, real account,
   market, holding, trade, credential, or provider data.
9. CI passes on Python 3.12, 3.13, and 3.14 and uses read-only repository
   permissions.
10. README language matches the limitations and makes no claim of adoption,
    external validation, security certification, model quality, or outcome.

## 10. Public positioning and release boundary

The public description may state that the tool:

- verifies a declared sample set and point-in-time cutoff;
- detects the six documented consistency violations;
- produces deterministic local receipts; and
- is covered by synthetic tests and public CI once those facts exist.

It must not claim that the tool:

- prevents all tampering or supplies an independent trusted timestamp;
- proves the truth, provenance, independence, or legal admissibility of data;
- validates a model, strategy, prediction, scientific finding, or return;
- has users, adoption, external validation, certification, or production use
  without public evidence.

The working public name is **Prospective Validation Ledger**, repository name
`prospective-validation-ledger`, and command `prospective-ledger`. Public name,
repository, distribution, and trademark availability must be checked again at
the time of publication. v0.1 targets GitHub only and does not include a PyPI
release, website, or hosted service.
