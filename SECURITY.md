# Security Policy

## Supported Versions

This project is pre-1.0. Security fixes are applied to the main branch.

## Privacy Model

The MVP is local-first. It does not upload models, contact Bambu cloud, read printer credentials, or send printer commands.

## Sensitive Data

Never commit:

- Personal STL, 3MF, G-code, screenshots, or generated reports
- Printer serial numbers, LAN access codes, or Bambu account tokens
- Local absolute paths from a real machine
- `.env` files or private keys

## Reporting Issues

Open a GitHub issue for non-sensitive bugs. For sensitive reports, use GitHub private vulnerability reporting if enabled by the repository owner.
