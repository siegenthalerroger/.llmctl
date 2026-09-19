"""Gates, packing, releasing and updating for an APM steering workspace.

One module per command, each exposing a typer `main` and the `cli` wrapper
pyproject.toml maps its console script to; the rest are the readers those
commands share. Every command takes the workspace it acts on as `--repo`,
so this code runs unchanged against any workspace laid out like this one.
"""
