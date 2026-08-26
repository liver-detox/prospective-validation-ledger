# Prospective Validation Ledger

Prospective Validation Ledger gives researchers and auditors a reproducible
eligibility check for a small validation bundle.

**On the first run:** verify the synthetic bundle and get either an `eligible`
receipt or a `rejected` receipt naming the rule that failed.

## Quickstart

From a local checkout, install the package with Python 3.12, 3.13, or 3.14,
then run the bundled synthetic example:

```bash
python -m pip install .
prospective-ledger verify examples/SYNTHETIC_eligible --out receipt.json
```

The command prints `eligible` and writes `receipt.json`. The bundled example
is entirely synthetic.

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
