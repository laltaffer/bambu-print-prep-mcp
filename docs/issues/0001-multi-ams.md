# Multi-AMS filament review

Status: implemented; live multi-AMS review/printing not yet tested

Extend the approved Connect submission flow to every AMS slot reported by the
selected printer. Keep exactly one plate numbered 1 and the existing chat approval,
readiness, expiration and one-attempt rules. Do not auto-select or change mappings.

## Acceptance

- Read all detected slots from the requested printer's device page, including
  ordinary AMS, AMS HT and AMS lite slot labels. Do not hardcode a unit count.
- Return every used sliced filament in displayed order with its one-based review
  index, source material, selected AMS slot and target material. Include the full
  detected slot inventory, including empty or unknown slots.
- Require complete row coverage against the plate's displayed filament list;
  unresolved, ambiguous, missing, empty or non-detected target mappings fail closed.
- Bind the whole mapping list and inventory into the approval digest. Recheck the
  full mapping list and freshly detected inventory before Send. Any change requires
  fresh approval. Existing single-filament jobs remain supported.
- Keep external-spool and multi-nozzle routing unsupported. No printer action is
  authorized by implementing this extension.

## Seams and verification

Use the existing SubmissionService preparation/submission boundary with a fake
external Connect UI, and the bundled native review-parser fixture boundary. Cover
several units, repeated materials, AMS HT/lite, partial or unresolved rows, changed
last-row mappings, and changed/disconnected detected slots. Typecheck Swift and
run the full MCP suite and lint. Live review requires an idle printer; physical
Send requires a newly approved job. Fixtures do not establish hardware support.
