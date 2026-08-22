# A synthetic three-tool evidence workflow

This tutorial connects three independent command-line tools through a small,
manual handoff:

1. [EvidenceReach](https://github.com/liver-detox/evidence-reach) assesses
   whether named evidence-supply scenarios can reach a required mature sample
   size.
2. [Prospective Validation Ledger](https://github.com/liver-detox/prospective-validation-ledger)
   checks the declared timing and internal consistency of a validation bundle.
3. [Decision Evidence Ledger](https://github.com/liver-detox/decision-evidence-ledger)
   binds a decision record to digests of the two upstream artifacts.

The tools remain separate. The handoff below is explicit and local; there is
no hidden integration layer or network service.

## The result to expect

The bundled EvidenceReach plan requires 128 mature observations, and all of
its supplied scenarios are `SCENARIO_NOT_REACHABLE_WITHIN_TERM`. The bundled
Prospective Validation Ledger example is `eligible`, with two accepted ledger
entries and no rejected entries. The example decision is therefore
`REVISE_COLLECTION_PLAN`: internal eligibility does not make the planned
sample size reachable.

The two upstream fixtures are separate, fabricated examples assembled into a
single fictional review packet to demonstrate the handoff. They are not one
empirical study or a shared dataset.

## 1. Prepare tagged source checkouts

Use Python 3.12, 3.13, or 3.14. From an empty working directory:

```bash
git clone --branch v0.1.0 --depth 1 https://github.com/liver-detox/evidence-reach.git
git clone --branch v0.1.0 --depth 1 https://github.com/liver-detox/prospective-validation-ledger.git
git clone --branch v0.1.0 --depth 1 https://github.com/liver-detox/decision-evidence-ledger.git

python3 -m venv .venv
source .venv/bin/activate
python -m pip install ./evidence-reach ./prospective-validation-ledger ./decision-evidence-ledger
mkdir demo
```

The installation downloads EvidenceReach's SciPy dependency. The other two
tools have no third-party runtime dependencies.

## 2. Assess sample reachability

```bash
evidence-reach assess \
  --plan evidence-reach/examples/SYNTHETIC_plan.json \
  --out demo/evidence-reach
```

The command creates `assessment.json`, `reachability.csv`, and `summary.md`.
The machine-readable assessment includes the exact input `plan_sha256`, the
calculated `required_n`, and one reachability state for every scenario and
horizon.

## 3. Verify the prospective bundle

```bash
prospective-ledger verify \
  prospective-validation-ledger/examples/SYNTHETIC_eligible \
  --out demo/validation-receipt.json
```

The command prints `eligible`. Its receipt includes the input digests,
accepted and rejected counts, rule and tool versions, and a `receipt_digest`.

## 4. Build the decision payload

This standard-library snippet reads both outputs, records their exact file
digests and small summaries, and writes a payload containing no source data:

```bash
python - <<'PY'
import hashlib
import json
from pathlib import Path


def read_artifact(path):
    raw = Path(path).read_bytes()
    return raw, json.loads(raw)


assessment_raw, assessment = read_artifact("demo/evidence-reach/assessment.json")
receipt_raw, receipt = read_artifact("demo/validation-receipt.json")

payload = {
    "schema_version": "1",
    "case_id": "SYNTHETIC-THREE-TOOL-001",
    "decision": "REVISE_COLLECTION_PLAN",
    "reason_codes": ["SYNTHETIC_SCENARIOS_NOT_REACHABLE"],
    "evidence_references": [
        {
            "tool": "EvidenceReach",
            "tool_version": "0.1.0",
            "artifact": "assessment.json",
            "artifact_sha256": hashlib.sha256(assessment_raw).hexdigest(),
            "plan_sha256": assessment["plan_sha256"],
            "required_n": assessment["statistics"]["required_n"],
            "scenario_states": sorted(
                {row["state"] for row in assessment["reachability"]}
            ),
        },
        {
            "tool": "Prospective Validation Ledger",
            "tool_version": receipt["tool_version"],
            "artifact": "validation-receipt.json",
            "artifact_sha256": hashlib.sha256(receipt_raw).hexdigest(),
            "experiment_id": receipt["experiment_id"],
            "receipt_digest": receipt["receipt_digest"],
            "status": receipt["status"],
            "accepted_count": receipt["accepted_count"],
            "rejected_count": receipt["rejected_count"],
        },
    ],
}
metadata = {
    "source_kind": "SYNTHETIC_TUTORIAL",
    "workflow_id": "SYNTHETIC-THREE-TOOL-001",
}

Path("demo/decision-payload.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
Path("demo/decision-metadata.json").write_text(
    json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
```

## 5. Seal and verify the decision record

```bash
decision-evidence seal \
  --event-id SYNTHETIC-WORKFLOW-EVENT-001 \
  --event-type SYNTHETIC-RESEARCH-DECISION \
  --subject-id SYNTHETIC-WORKFLOW-001 \
  --operation ASSERT \
  --recorded-at 2030-01-02T03:04:05.000001Z \
  --payload demo/decision-payload.json \
  --metadata demo/decision-metadata.json \
  > demo/seal-result.json

python - <<'PY'
import json
from pathlib import Path

result = json.loads(Path("demo/seal-result.json").read_text(encoding="utf-8"))
envelope = json.dumps(
    result["envelope"], sort_keys=True, separators=(",", ":")
) + "\n"
Path("demo/decision-envelope.json").write_text(envelope, encoding="utf-8")
Path("demo/decision-ledger.jsonl").write_text(envelope, encoding="utf-8")
PY

decision-evidence verify-envelope \
  --envelope demo/decision-envelope.json \
  --payload demo/decision-payload.json \
  --metadata demo/decision-metadata.json

decision-evidence verify-chain --ledger demo/decision-ledger.jsonl
```

The first verification should report `"ok":true`. The chain verification
should report `"ok":true` with one event and a head digest.

## What the chain establishes

- EvidenceReach makes the sample-size and supply assumptions inspectable; its
  reachability state is scenario arithmetic, not a forecast.
- Prospective Validation Ledger records declared timing and internal
  consistency; `eligible` does not prove source truth or statistical power.
- Decision Evidence Ledger binds the decision payload to exact digests; it
  does not fetch or authenticate the upstream artifacts. A later reviewer must
  recompute the two `artifact_sha256` values against retained copies.

Everything in this walkthrough is synthetic. It contains no account, holding,
trade, provider credential, personal record, private path, or licensed dataset.
