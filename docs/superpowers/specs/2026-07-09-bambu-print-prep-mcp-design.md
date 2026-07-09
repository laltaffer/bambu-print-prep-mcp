# Bambu Print Prep MCP Design

## Purpose

Build a local-first MCP server that lets a user's AI assistant prepare 3D models for Bambu Studio without requiring 3D modeling experience. The first milestone focuses on model inspection, repair, scale normalization, print-setting recommendations, and safe export. It does not connect to a Bambu printer, send print jobs, scrape MakerWorld, or automate Bambu Studio's GUI.

## Public Repository Goals

This project is intended to become a public GitHub repository. The repository must not include private models, printer serial numbers, printer access codes, account tokens, local user paths, machine-specific cache paths, screenshots with private data, or generated files that expose a user's filesystem.

The project should include a public-safe `.gitignore`, sample configuration files that use placeholders, and documentation that explains how to provide local file paths at runtime without committing them. Before the first public push, the repository should be scanned for secrets and reviewed for accidental local metadata. The current `AGENTS.md` file contains local session metadata and should not be committed publicly as-is.

## Scope

The MVP accepts a local STL file path, analyzes the model, optionally repairs it, normalizes obvious unit or scale problems, recommends Bambu Studio settings, and writes outputs that are easy to use manually in Bambu Studio.

Supported model input for the MVP:
- STL files, both binary and ASCII.

Out of scope for the MVP:
- Direct printer control.
- Bambu cloud login.
- LAN printer credentials.
- Sending print jobs.
- MakerWorld account integration.
- GUI automation of Bambu Studio.
- Freeform LLM mesh editing.
- Guaranteed repair of severely damaged meshes.

## User Workflows

### Inspect a Model

The user gives the MCP server a local STL path. The server returns dimensions in millimeters, triangle count, bounding box, volume if available, basic manifold health, suspicious scale warnings, and printability notes.

### Repair a Model

The user asks the AI assistant to repair an STL. The server writes a repaired STL to an output directory, preserving the original file untouched. The result includes a repair summary and post-repair inspection.

### Normalize Scale

The user provides a target height, width, depth, or original dimensions. The server scales the repaired model and writes a new STL. It flags likely meter-to-millimeter or inch-to-millimeter mistakes when dimensions are far outside a selected Bambu printer's build volume.

### Recommend Bambu Settings

The user asks how to print a model on a Bambu printer with a selected material. The server returns practical Bambu Studio settings such as layer height, support type, support placement, threshold angle, support interface guidance, brim guidance, wall count, infill guidance, and warnings.

### Prepare for Bambu

The user asks for a single operation that prepares a model. The server inspects, repairs if needed, scales if requested, recommends print settings, and writes a report beside the output STL.

## MCP Tools

### `inspect_model`

Input:
- `file_path`: absolute or workspace-relative STL path.
- `printer`: optional printer profile name, default `bambu_lab_p2s`.

Output:
- Dimensions in millimeters.
- Triangle count.
- Bounding box.
- Volume estimate when available.
- Watertight/manifold indicators when available.
- Build-volume fit result.
- Suspicious-scale warnings.
- Human-readable summary.

### `repair_model`

Input:
- `file_path`: STL path.
- `output_path`: optional output STL path.
- `preserve_scale`: boolean, default `true`.

Output:
- Output STL path.
- Before and after model inspection.
- Repair actions attempted.
- Warnings when repair could not confidently make the model printable.

### `normalize_scale`

Input:
- `file_path`: STL path.
- `output_path`: optional output STL path.
- `target_height_mm`: optional number.
- `target_width_mm`: optional number.
- `target_depth_mm`: optional number.
- `scale_factor`: optional number.
- `printer`: optional printer profile name.

Output:
- Output STL path.
- Original dimensions.
- New dimensions.
- Applied scale factor.
- Build-volume fit result.

### `recommend_print_settings`

Input:
- `file_path`: STL path.
- `printer`: printer profile name, default `bambu_lab_p2s`.
- `material`: material profile name, default `PLA`.
- `intent`: optional value such as `statue`, `functional`, `miniature`, `terrain`, or `fast_draft`.

Output:
- Recommended layer height.
- Support strategy.
- Adhesion settings.
- Strength and quality settings.
- Risk notes.
- Exact plain-English steps for Bambu Studio.

### `prepare_model_for_bambu`

Input:
- `file_path`: STL path.
- `output_dir`: optional output directory.
- `printer`: printer profile name, default `bambu_lab_p2s`.
- `material`: material profile name, default `PLA`.
- `target_height_mm`: optional number.
- `intent`: optional print intent.

Output:
- Final STL path.
- Markdown report path.
- JSON report path.
- Inspection before and after repair/scale.
- Recommended Bambu Studio settings.
- Remaining risks and manual checks.

## Architecture

The project should be a small Python package with a thin MCP server layer and a separate geometry core. The MCP layer should validate inputs, call core services, and serialize results. The geometry core should be usable from tests without MCP transport.

Primary modules:
- MCP server: exposes tools and converts tool inputs to core calls.
- Model I/O: loads and writes STL files.
- Analysis service: computes dimensions, triangle count, bounding boxes, and fit checks.
- Repair service: performs local mesh repair where possible.
- Transform service: scales models and preserves originals.
- Recommendation service: maps model geometry, material, printer, and intent to Bambu settings.
- Reporting service: writes Markdown and JSON outputs.
- Security utilities: constrain outputs, redact local paths in reports when needed, and prevent accidental credential inclusion.

## Data Model

Printer profiles should be static data files in the repository. The MVP should include `bambu_lab_p2s` because that is the user's current printer context. Profiles should define build volume, nozzle defaults, and common material assumptions without storing any device-specific identifiers.

Reports should include input and output paths for local usability, but public documentation and tests must use temporary or fixture paths only. Generated reports should not be committed unless they are synthetic test fixtures with safe paths.

## Error Handling

The server should never overwrite the original input model unless an explicit overwrite option is added in a future version. Missing files, unsupported file types, unreadable meshes, failed repairs, invalid target dimensions, and output path conflicts should return structured errors with a short human-readable fix.

When repair succeeds technically but the model still appears risky, the tool should return a warning rather than pretending the model is guaranteed printable.

## Security And Privacy

The MVP must avoid network access during normal operation. It should not upload models to online repair services. It should not read Bambu credentials, cloud tokens, printer serial numbers, or LAN access codes.

Before public release:
- Add `.gitignore` entries for local configs, generated output, model files, logs, caches, and environment files.
- Add a placeholder `.env.example` only if configuration becomes necessary.
- Run a secret scan.
- Review `git status` and staged files manually.
- Do not commit `AGENTS.md` unless it is replaced with a sanitized public version.
- Do not commit user STL files or screenshots.

## Testing Strategy

Tests should use synthetic generated meshes rather than personal downloaded models. Fixtures should cover a valid cube, an oversized model that triggers scale warnings, a model with known non-manifold or open-edge behavior if practical, and recommendation outputs for a statue-like model.

Core services should be tested directly. MCP tools should have integration tests that verify input validation and response shape.

## Future Milestones

After the local-first print-prep MVP works, later milestones can add:
- 3MF project generation.
- Bambu/Orca slicer profile generation.
- G-code or slicing preview analysis.
- Safe LAN printer status monitoring.
- Photo-assisted print failure diagnosis.
- LLM-guided model edits through explicit geometry tools such as add text, split model, add connectors, hollow model, and boolean cuts.

Future direct printer control must require explicit user confirmation for any action that changes printer state.

## Acceptance Criteria

The MVP is complete when a user can point the AI assistant at an STL file and receive a repaired or scale-corrected output STL plus clear Bambu Studio settings without using a modeling app. The original STL remains unchanged. The tool works without network access. The repository can be safely made public after following the documented security checklist.
