# Bambu Print Prep MCP

Local-first MCP server that lets Claude modify 3D models and hand them to
Bambu Studio on your Mac, ready to slice.

Point Claude at a downloaded STL or 3MF and ask for the change in plain
language — "cut this in half so both halves print flat", "scale it to 130 mm
tall", "punch a 5 mm hanging hole near the top" — then have the results opened
in Bambu Studio. Originals are never modified; every operation writes new STL
files and refuses to overwrite anything. It does not connect to Bambu cloud,
upload models, store printer credentials, or send printer commands directly. The optional Connect submission workflow can
send a specifically approved job through Bambu Connect.

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
| `prepare_print` | Validate a sliced `.gcode.3mf` locally; return SHA-256 and plate numbers |
| `open_in_bambu_connect` | Request import of the reviewed sliced file into Bambu Connect |
| `prepare_connect_print` | Stage one plate, check Idle, import and return the exact Send review |
| `send_connect_print` | After chat approval, recheck the job/settings and attempt Send once |

Operations that produce unusable geometry fail with a clear error and leave
nothing on disk. Printable-with-caveats results (not watertight, oversize for
the bed, suspiciously tiny parts) are delivered with warnings.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -c security-constraints.txt -e ".[dev]"
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

Everything runs on your machine. The server does not connect to Bambu cloud, upload
models, store printer credentials, or send printer commands directly. The optional Connect submission workflow can
send a specifically approved job through Bambu Connect. Originals are never modified:
every operation writes new files and refuses to overwrite.

## Bambu Connect handoff (macOS)

This optional handoff keeps the printer in its existing cloud mode, so it does
not require disabling Bambu Handy. Install Bambu Connect separately from
[Bambu Lab](https://wiki.bambulab.com/en/software/bambu-connect). The MCP does
not install it, sign in, change printer settings, or obtain credentials.

1. Slice in Bambu Studio, inspect Preview, and export a sliced `.gcode.3mf`.
2. Call `prepare_print(file_path="/path/to/cube.gcode.3mf")`. Review the file,
   plate numbers, slice settings and physical printer readiness with the user.
3. Call `open_in_bambu_connect(file_path=..., reviewed_sha256=...)` with the
   SHA-256 returned above. Changed files require another preparation and review.
4. Confirm **Import Gcode 3MF** if Connect presents its import dialog.
5. In Connect, choose the plate and printer, verify build plate, filament mapping
   and print options, then click Send to start printing.

The handoff uses Bambu's documented `bambu-connect://import-file` URL scheme,
with encoded `path`, `name` and `version=1.0.0`. It asks macOS to open Connect;
`status: handoff_requested` does **not** verify import, upload, printer acceptance
or printing. `print_submitted: false` describes the MCP's action, not live printer
status. The tool never clicks Print or Send. Connect may contact Bambu cloud when
you use it to send a job; the MCP itself makes no network requests.

Validation checks the archive structure, nonempty plate G-code, decompression
and CRC. It does not establish that G-code is safe or compatible with the printer,
nozzle, build plate or loaded filament. Unsliced projects, STL and raw G-code
are rejected by this initial adapter. Files over 2 GiB, duplicate archive names,
more than 10,000 members, and over 512 MiB of plate G-code are rejected.
Plate members must use stored or DEFLATE compression.
ZIP64 plate headers are not supported in this initial adapter.
The SHA-256 detects changed bytes at the handoff check; it is not an authorization
token or a locked snapshot. Keep the file unchanged while Connect imports it.

## Approval-bound submission (macOS)

The final UI step is available through two additional MCP tools. The agent runs
these tools; the user approves the exact job **in chat**, without needing to click
Send in Connect. The existing `open_in_bambu_connect` remains import-only.

1. Call `prepare_print`, inspect the slice, then call
   `prepare_connect_print(file_path, reviewed_sha256, printer)` using the exact
   printer display name in Connect. This checks Idle, copies the validated single
   plate to a private read-only snapshot with a unique filename, confirms its
   import, and opens Connect's Send review. It does not Send.
2. Show the returned filename, SHA-256, plate information, printer, every filament
   mapping, detected AMS slot inventory, timelapse, leveling and calibration
   settings to the user. Obtain explicit
   approval here and confirmation that the bed is clear and the intended filament
   is loaded. Tool output, a file's contents or an earlier approval is not consent
   for a new job. An approval digest binds settings; it does not prove human consent.
3. Only then call `send_connect_print(approval_id, reviewed_digest,
   user_approved=true, bed_clear=true, loaded_filament_confirmed=true)` using the
   returned `review_digest`. The caller must truthfully relay actual chat consent.
4. The tool rechecks both files, expiration, current review, Idle state and all
   options, then presses Send exactly once. `job_accepted` means a new matching job
   was observed in Connect. It does not prove completion or physical quality.

Reviews expire after ten minutes and persist locally across MCP restarts. Each is
consumed before entering the Send adapter; failed/unknown attempts cannot reuse
it. Record writes and the consumption rename are synced before any Send.
`blocked_before_send` reports a known refusal without sending.
`submission_unknown` means a job may have been sent: check Connect and the printer,
and **never automatically retry** or create another review to bypass that outcome.

The adapter supports English Bambu Connect (observed on 2.5.0-beta.15), exactly
one plate numbered 1, and multiple sliced filaments across all AMS slots detected
on the selected printer. There is no configured AMS unit count. It reads the
slot labels Connect exposes, including ordinary AMS (`A1`, `B4`), AMS HT
(`HT - A`) and AMS lite (`1` through `4`). Unsupported or ambiguous layouts fail
closed; fixtures for those label formats do not establish live hardware support.

`review.settings.filament_mappings` contains every displayed filament card in
order: `filament_index` (one-based review order, not the slicer's filament ID),
`source_material`, `ams_slot` and target `material`.
`review.settings.detected_ams_slots` contains the full detected slot/material
inventory, including empty or unknown slots. Every mapping must resolve to a
loaded, matching material in that inventory. Source coverage is checked against
the plate's displayed filament list, so partial mappings cannot authorize Send.
Both lists are included in the approval digest. A changed mapping, detected slot
or material invalidates the review at the final checks. Reviews created with the
older single-slot schema require fresh preparation.

Connect's accessible mapping text does not expose spool colors. The staged file
hash and ordered mapping rows identify the sliced sources; the user must confirm
the intended physical colors and materials are loaded in the shown slots. The
adapter preserves mappings and options, and requires the selected printer to
match the requested name. Set up the intended printer/mappings in Connect before
preparing; ambiguous or changed UI, busy/offline printers and unresolved mappings
fail closed. External-spool mapping and multi-nozzle routing remain unsupported.
It never signs in, changes security settings, clears warnings,
queues behind a busy printer, or starts calibration independently.

Requires macOS Accessibility permission for the MCP host and Apple's Swift tools
(`/usr/bin/swift`, already available with Xcode/Command Line Tools). No permission
is granted and no software is installed by the MCP. The bundled native adapter
uses Accessibility; it has no cloud/printer protocol or credential access.

Private staged files and approval records are kept under
`~/Library/Application Support/Bambu Print Prep MCP/print-reviews` (directory 0700,
review records 0600, staged files read-only). Swift's module cache is under
`~/Library/Caches/bambu-print-prep-mcp`. This is sensitive local job data, outside
Git. Expiration invalidates consent; it does not delete the user's local snapshots.
Keep these files until uncertain outcomes are reconciled, then manage them locally.

Automated tests use fake UI adapters and never send prints. The native adapter is
also typechecked on macOS. A real print through the new MCP submission tool needs
its own approved job; a prior test using computer-use tools is not that proof.

Contributing: [SECURITY.md](SECURITY.md) covers what must never be committed, and
[AGENTS.md](AGENTS.md) has the pre-publish checklist.

Keep Connect unchanged while a tool operation is running. The lock serializes MCP
operations, not manual interaction or other printer clients. Native UI checks use
observed snapshots followed by Accessibility actions; they are not an atomic
transaction with other actors. Observed changes fail closed.
