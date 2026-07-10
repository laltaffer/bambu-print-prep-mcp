# Bambu Print Prep MCP

Local-first MCP server that lets Claude modify 3D models and hand them to
Bambu Studio on your Mac, ready to slice.

Point Claude at a downloaded STL or 3MF and ask for the change in plain
language — "cut this in half so both halves print flat", "scale it to 130 mm
tall", "punch a 5 mm hanging hole near the top" — then have the results opened
in Bambu Studio. Originals are never modified; every operation writes new STL
files and refuses to overwrite anything. It does not connect to Bambu cloud,
upload models, store printer credentials, or send print jobs.

## Tools

| Tool | What it does |
|------|--------------|
| `inspect_model` | Dimensions, triangle count, watertightness, build-volume fit, warnings |
| `repair_model` | Fix normals/winding, fill holes, drop degenerate geometry |
| `scale_by_factor` | Uniform scale by a factor |
| `scale_to_dimension` | Scale so width/depth/height hits a target in mm |
| `cut_plane` | Cut in two along an axis, cap both faces, lay parts cut-face-down |
| `split_parts` | Separate a multi-part model into one file per component |
| `mirror_model` | Reflect across a plane (printable, winding corrected) |
| `rotate_model` | Rotate around an axis, then rest on the bed |
| `punch_hole` | Boolean-subtract a cylindrical hole (through or blind) |
| `open_in_bambu_studio` | Open finished files in Bambu Studio |

Operations that produce unusable geometry fail with a clear error and leave
nothing on disk. Printable-with-caveats results (not watertight, oversize for
the bed, suspiciously tiny parts) are delivered with warnings.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## MCP Server

```bash
bambu-print-prep-mcp
```

Register with an MCP client (e.g. Claude Code):

```bash
claude mcp add bambu-print-prep -- /path/to/.venv/bin/bambu-print-prep-mcp
```

## CLI Smoke Test

```bash
bambu-print-prep inspect /path/to/model.stl
```

## Privacy

Do not commit personal STL files, screenshots, printer serials, access codes,
Bambu account data, or local absolute paths. Generated output belongs in
`outputs/` directories, which are ignored by git.

## Public Repository Safety Checklist

Before pushing publicly:

- Run `git status --short` and review every tracked file.
- Search tracked source files for local machine paths, personal identifiers, credentials, and generated-file metadata.
- Run `detect-secrets-hook --baseline .secrets.baseline $(git ls-files)` and confirm it exits 0.
- Confirm no personal model files, screenshots, printer identifiers, or local paths are staged.
- Confirm generated outputs remain under ignored directories such as `outputs/`.
