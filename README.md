# Prospective Validation Ledger

Prospective Validation Ledger gives researchers and auditors a reproducible
eligibility check for a small validation bundle.

In an optional three-tool workflow, Prospective Validation Ledger is the cutoff
step: does the declared bundle satisfy its timing and consistency rules?

**On the first run:** create a complete synthetic bundle from a draft, then
verify it to get either an `eligible` receipt or a `rejected` receipt naming
the rule that failed.

## Quickstart

From a local checkout, install the package with Python 3.12, 3.13, or 3.14,
then copy the bundled synthetic draft, create a bundle, and verify it:

```bash
python -m pip install .
mkdir demo
cp -R examples/SYNTHETIC_draft demo/draft
prospective-ledger create demo/draft --out demo/bundle
prospective-ledger verify demo/bundle --out demo/receipt.json
python -m json.tool demo/receipt.json
```

The create command prints `created`; verification prints `eligible` and writes
`demo/receipt.json`. The final command shows the receipt: start with `status`,
`accepted_count`, `rejected_count`, and `violations`. The input and receipt
digests make repeat runs over the same valid bundle deterministic. The bundled
example is entirely synthetic; copying it keeps the repository fixture unchanged
while you inspect the three input files.

To create a real bundle, begin from the copied draft file shapes. Drafts omit
the derived snapshot and ledger entry digests; `create` validates their structure
and computes those fields before verification.

## What an eligibility receipt checks

The tool reads a plan, a snapshot, and a ledger. It checks the declared cutoff
timing, sample membership, ledger continuity, duplicate entries, and the
digests that tie the bundle together. It then writes a deterministic receipt
describing whether the bundle is eligible or rejected.

### The three input files

A bundle directory contains three files:

- `plan.json` declares the experiment, cutoff, sample IDs, and snapshot digest.
- `snapshot.json` declares the snapshot timing and record count.
- `ledger.jsonl` records one compact JSON object per evidence entry.

### Eligible and rejected receipts

An `eligible` receipt has no violations. A `rejected` receipt lists violations
and accepted/rejected entry counts. Input and receipt digests make repeated
runs over the same valid bundle produce the same compact JSON.

## When a bundle is rejected

The verifier can report these six codes:

- `DIGEST_MISMATCH`
- `LEDGER_GAP`
- `DUPLICATE_ENTRY`
- `UNKNOWN_SAMPLE`
- `POST_CUTOFF_EVENT`
- `LATE_ARRIVAL`

### Common local failures

- A structural error identifies the affected file and safe error category or
  field, such as `plan.json has invalid JSON`. It never echoes supplied values
  or payload content.
- `rejected` writes a receipt and exits non-zero. Read its `violations` array;
  this differs from a structural error, which writes no new receipt.
- Both commands require the output parent directory to exist. `create` requires
  a new bundle path; `verify` cannot replace `plan.json`, `snapshot.json`, or
  `ledger.jsonl`.

## Use it in the three-tool workflow

For a complete synthetic handoff across EvidenceReach, Prospective Validation
Ledger, and Decision Evidence Ledger, see the
[three-tool workflow tutorial](docs/SYNTHETIC_THREE_TOOL_WORKFLOW.md).

## Boundaries and data handling

The tool checks declared timing and internal consistency; it does not provide
trusted timestamps, absolute tamper prevention, source truth, model validation,
prediction quality, or investment analysis. v0.1 targets small local bundles
and does not enforce adversarial resource quotas.

Fixtures are synthetic, and the tool neither requires nor uploads payloads.
Use pseudonymous sample IDs because rejected receipts expose IDs. No network,
provider, account, or execution adapter is included. Do not commit real or
licensed datasets; see [DATA_POLICY.md](DATA_POLICY.md).

## Development and test command

Run the complete test suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

## License

Prospective Validation Ledger is licensed under the [Apache License 2.0](LICENSE).
