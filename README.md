# Bambu Print Prep MCP

Local-first MCP server for preparing STL files for Bambu Studio.

The MVP inspects STL files, repairs simple mesh problems, normalizes scale, recommends Bambu Studio settings, and writes safe local reports. It does not connect to Bambu cloud, upload models, store printer credentials, or send print jobs.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## CLI Smoke Test

```bash
bambu-print-prep inspect /path/to/model.stl
```

## MCP Server

```bash
bambu-print-prep-mcp
```

## Privacy

Do not commit personal STL files, screenshots, generated reports, printer serials, access codes, Bambu account data, or local absolute paths. Generated output belongs in `outputs/`, which is ignored by git.

## Public Repository Safety Checklist

Before pushing publicly:

- Run `git status --short` and review every tracked file.
- Search tracked source files for local machine paths, personal identifiers, credentials, and generated-file metadata.
- Run `detect-secrets-hook --baseline .secrets.baseline $(git ls-files)` and confirm it exits 0.
- Confirm no personal model files, screenshots, reports, printer identifiers, or local paths are staged.
- Confirm generated outputs remain under ignored directories such as `outputs/`.
