# Optional local DVC capture for the synthetic three-tool workflow

Complete the [synthetic three-tool workflow](SYNTHETIC_THREE_TOOL_WORKFLOW.md)
first. This optional example makes a local DVC-tracked copy of its synthetic
`demo/` outputs. It is not an integration, does not configure a remote, and
does not upload the captured artifacts.

If DVC is not already available in your environment, install it separately:

```bash
python -m pip install dvc
```

From the working directory that contains the completed tutorial's `demo/`
directory, make an independent capture directory and initialize DVC without
source-control integration:

```bash
mkdir capture-dvc
cp -R demo capture-dvc/demo
cd capture-dvc
dvc init --no-scm
dvc add demo
dvc status
```

`dvc add` creates `demo.dvc` and a local `.dvc/cache/`; review those files
before sharing.
