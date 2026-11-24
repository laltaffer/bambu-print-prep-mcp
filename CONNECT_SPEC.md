# Bambu Connect adapter: validation, review and approved submission

Approved direction: extend the existing MCP with a Connect adapter while keeping
Bambu Handy available. Use Bambu's documented file-import URL, not direct printer
control or a cloud API. The initial import handoff is retained. The approved extension adds agent-executed Send after chat approval.

- Add `prepare_print(file_path)` and `open_in_bambu_connect(file_path, reviewed_sha256)`.
- Accept only sliced `.gcode.3mf` archives with nonempty `Metadata/plate_N.gcode`.
- Inspect locally without extraction, credentials, account changes or network calls.
- Return SHA-256 and sorted plate IDs. Explain structural validation limits.
- Validate decompression/CRC and reject malformed, duplicate, encrypted or oversized
  plate data. Limit archive size to 2 GiB, entries to 10,000 and plate data to 512 MiB.
  Accept stored and DEFLATE plate members; check actual decoded length and CRC.
  Require consistent local headers or streaming data descriptors; reject ZIP64 plates.
- Refuse a changed file or invalid hash before launching an app.
- Encode the absolute path and filename into the official import URL with version 1.0.0.
- Launch Bambu Connect explicitly using an argument vector and a bounded timeout.
- Report only `handoff_requested` and `print_submitted: false`; do not claim verified import.
- Give actionable launch errors; never click Print/Send or change printer state.
- Preserve existing tools and source files. Add no runtime dependencies.

## Approved submission extension

- Add `prepare_connect_print(file_path, reviewed_sha256, printer)` and
  `send_connect_print(approval_id, reviewed_digest, user_approved=false,
  bed_clear=false, loaded_filament_confirmed=false)`.
- Preparing checks an exactly named Idle printer, makes a uniquely named private
  read-only copy, confirms Connect import, opens review and returns the exact job,
  printer, plate metadata, material, AMS slot, timelapse, leveling and calibration.
- Preparing never presses Send. Single plate 1 and one resolved AMS slot only.
- Chat approval and physical readiness confirmations are supplied by the caller;
  the MCP cannot independently authenticate what the user said in chat. Never
  describe a boolean/hash as independent human authorization.
- Bind each review to source/snapshot hashes and all observed settings. Expire it
  in ten minutes, recheck expiration immediately before Send, and serialize MCP
  review/submission operations across processes.
- Persist one-use consumption before any possible Send. Replays/process restarts
  cannot repeat an attempted job. Native adapter attempts final Send once, with no
  retries or warning bypass. Unknown outcomes require human reconciliation.
- Immediately before Send verify review, Idle state, staged filename/plate metadata,
  selected printer/mapping/options again. Different or ambiguous UI fails closed.
- `job_accepted` requires observing a new matching job. A timeout is
  `submission_unknown`; known pre-send refusal is `blocked_before_send`.
- Bundle the macOS Accessibility Swift adapter as package data; no pip dependency
  changes. It does not acquire permissions, sign in or handle credentials.
- No live Send test is authorized merely by the implementation request. Exercise
  failure/approval/replay/concurrency through fakes and typecheck native source;
  stop live smoke at review until Lawrence approves a new specific test job.

Not included: automatic slicing, automatic printer/filament selection, multi-plate
or multi-filament printing, external-spool mapping, auth, installation, firmware,
independent hardware calibration, unattended queuing or blanket print authority.
The initial import-only no-Send bullets above describe the retained original tools,
not the new explicitly approved submission tool.

Reference: https://wiki.bambulab.com/en/software/bambu-connect

Concurrency boundary: a file/metadata snapshot supplies the exact Print control;
the final fresh dialog snapshot supplies both complete settings validation and
the Send control. UI state checks cannot be atomic with a person operating the
app or another printer client. The operator must leave Connect unchanged during
an operation. Consumption is synced to disk before entering the Send adapter.
