# Security Policy

## Supported Versions

This project is pre-1.0. Security fixes are applied to the main branch.

## Privacy Model

The MVP is local-first. It does not upload models, contact Bambu cloud, read printer credentials, or send printer commands.

The optional Bambu Connect adapter validates sliced archives locally and requests
file import through Connect's documented URL scheme. The original import-only tool does not submit a print,
control the printer or read account data. The separate approved submission tool
described below can Send a reviewed job. Bambu Connect is a separate application
that may use Bambu cloud when the user sends a job. A successful handoff request
does not prove the file imported or the printer accepted a job. A file hash checks
for changed bytes, not user authorization or physical print readiness.

## Sensitive Data

Never commit:

- Personal STL, 3MF, G-code, screenshots, or generated reports
- Printer serial numbers, LAN access codes, or Bambu account tokens
- Local absolute paths from a real machine
- `.env` files or private keys

## Reporting Issues

Open a GitHub issue for non-sensitive bugs. For sensitive reports, use GitHub private vulnerability reporting if enabled by the repository owner.


## Approved Connect submission

The optional preparation/submission tools can import and Send one reviewed job
through the already-authenticated Bambu Connect app, which may upload that model
to Bambu cloud. Human approval is enforced by the calling agent/client's actual
chat interaction; boolean confirmations and review digests alone cannot establish
that a human approved. The MCP refuses absent confirmation, mismatched/expired
reviews and changed bytes/settings, consumes attempts persistently and never
automatically retries uncertain outcomes. Native Accessibility permission and
local app/session access are prerequisites, not permissions granted by the tool.

Private read-only staged copies and one-use review records live in the user's
Application Support directory, outside Git. They include local file paths and
printer display names, not serials, access codes, cloud tokens or account IDs.
Protect them as local job data. No confirmation scheme protects against a malicious
process already running as the same OS user and able to operate Connect itself.
