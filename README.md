# Prospective Validation Ledger

## 1. One-sentence purpose

Prospective Validation Ledger is a local command-line tool that checks declared timing and internal consistency in a small validation bundle.

## 2. What it verifies

The tool reads a plan, a snapshot, and a ledger. It checks the declared cutoff timing, sample membership, ledger continuity, duplicate entries, and the digests that tie the bundle together. It then writes a deterministic receipt describing whether the bundle is eligible or rejected.

## 3. What it does not prove

This tool does not provide trusted timestamping or absolute tamper prevention. It does not verify source truth, validate a model, assess prediction quality, perform investment analysis, demonstrate adoption, or provide external validation. v0.1 is intended for small local bundles and does not enforce adversarial resource quotas.

## 4. Installation from a local GitHub checkout

From a local checkout of this repository, install the package with Python 3.12, 3.13, or 3.14:

```bash
python -m pip install .
```

## 5. One-command synthetic quick start

```bash
python -m pip install .
prospective-ledger verify examples/SYNTHETIC_eligible --out receipt.json
```

The command prints `eligible` and writes `receipt.json`. The bundled example is entirely synthetic.

For a complete synthetic handoff across EvidenceReach, Prospective Validation
Ledger, and Decision Evidence Ledger, see the
[three-tool workflow tutorial](docs/SYNTHETIC_THREE_TOOL_WORKFLOW.md).

## 6. Three input files

A bundle directory contains three files:

- `plan.json` declares the experiment, cutoff, sample IDs, and snapshot digest.
- `snapshot.json` declares the snapshot timing and record count.
- `ledger.jsonl` records one compact JSON object per evidence entry.

## 7. eligible and rejected receipts

An `eligible` receipt has no violations. A `rejected` receipt lists the rule violations found and includes accepted and rejected entry counts. Receipts include input digests and a receipt digest so repeated runs over the same valid input produce the same compact JSON output.

## 8. Six violation codes

The verifier can report these six codes:

- `DIGEST_MISMATCH`
- `LEDGER_GAP`
- `DUPLICATE_ENTRY`
- `UNKNOWN_SAMPLE`
- `POST_CUTOFF_EVENT`
- `LATE_ARRIVAL`

## 9. Privacy and synthetic-data policy

This repository contains synthetic fixtures only. The tool does not require or upload payload content. Use pseudonymous sample IDs because rejected receipts expose IDs. No network, provider, account, holding, order, or execution adapter is included. Do not commit real or licensed datasets; see [DATA_POLICY.md](DATA_POLICY.md).

## 10. Development and test command

Run the complete test suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

## 11. License

Prospective Validation Ledger is licensed under the [Apache License 2.0](LICENSE).
