# Optional local MLflow capture for the synthetic three-tool workflow

Complete the [synthetic three-tool workflow](SYNTHETIC_THREE_TOOL_WORKFLOW.md)
first. This optional example records a local MLflow copy of its explicitly
listed synthetic artifacts. It is not an integration, does not start an MLflow
service, and does not upload the listed artifacts.

If MLflow is not already available in your environment, install it separately:

```bash
python -m pip install mlflow
```

From the working directory that contains the completed tutorial's `demo/`
directory, create the following short script. Its relative tracking URI keeps
the local store in `capture-mlflow/mlruns/` and avoids hard-coded paths.

```bash
mkdir capture-mlflow
cat > capture-mlflow/log_synthetic_artifacts.py <<'PY'
from pathlib import Path

import mlflow


mlflow.set_tracking_uri("file:./mlruns")

artifacts = {
    "evidence-reach": [
        "assessment.json",
        "reachability.csv",
        "summary.md",
    ],
    "prospective-validation-ledger": [
        "validation-receipt.json",
    ],
    "decision-evidence-ledger": [
        "decision-payload.json",
        "decision-metadata.json",
        "seal-result.json",
        "decision-envelope.json",
        "decision-ledger.jsonl",
    ],
}

demo = Path("../demo")
with mlflow.start_run():
    for tool, names in artifacts.items():
        for name in names:
            source = demo / tool / name if tool == "evidence-reach" else demo / name
            mlflow.log_artifact(str(source), artifact_path=tool)
PY

cd capture-mlflow
python log_synthetic_artifacts.py
```

This logs only the listed synthetic artifacts to local `mlruns/`, without
parameters or tags; review the directory before sharing.
