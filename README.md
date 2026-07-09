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
bambu-print-prep prepare /path/to/model.stl --target-height-mm 130 --output-dir outputs
```

## MCP Server

```bash
bambu-print-prep-mcp
```

## Privacy

Do not commit personal STL files, screenshots, generated reports, printer serials, access codes, Bambu account data, or local absolute paths. Generated output belongs in `outputs/`, which is ignored by git.
