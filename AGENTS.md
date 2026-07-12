# Agent Instructions

This repository builds a local-first MCP server that lets AI assistants modify 3D models (STL/3MF) and hand them to Bambu Studio on macOS.

## Privacy Rules

- Do not commit personal STL/3MF files, screenshots, generated reports, printer credentials, access codes, serial numbers, cloud tokens, or local machine paths.
- Keep examples synthetic and use sample paths such as `/path/to/model.stl`.
- The MVP must not upload models to network services.
- Any future printer-control feature must require explicit user confirmation before changing printer state.

## Development Rules

- Prefer small, testable modules under `src/bambu_print_prep_mcp`.
- Keep MCP tool wrappers thin; put business logic in core services.
- Run tests, linting, and secret scanning before publishing.
