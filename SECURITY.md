# Security and privacy policy

## Current scope

DayQuest is a local, synthetic-data prototype. The public evidence path is designed to avoid raw private payloads, credentials, email bodies, exact financial details, and absolute local paths. The localhost MCP server exposes only an allowlisted, redacted event projection.

## Safe local use

- Use the committed synthetic fixtures for demos and tests.
- Keep API keys and session tokens in an ignored local `.env`; never add them to fixtures, traces, screenshots, issues, or evaluation artifacts.
- Bind the development MCP endpoint to localhost unless a separately reviewed authentication boundary exists.
- Treat stable safe-event IDs as identifiers for an already allowed projection, not as encryption or anonymization.
- Review generated artifacts with `python -B scripts/scan_public_artifacts.py` before any future publication.

## What the automated scan covers

The repository scan checks tracked sensitive filenames and committed JSON/JSONL artifacts for Windows drive-letter absolute paths, email-shaped text, and Bearer/sk-like token text. It deliberately does not read ignored `.env` files. Passing the scan is not general secret scanning, private-data validation, cross-platform path coverage, penetration testing, or security certification.

## Known security boundaries

The project does not claim a production sandbox, tenant isolation, arbitrary-tool permission enforcement, hostile-input resistance, live-provider security, or externally validated CI. Remote provider paths remain optional; the no-key local path is the reproducible evidence route.

## Reporting

Until a public repository and maintainer contact are explicitly approved, do not send private vulnerability details externally. Preserve a minimal local reproduction and request a user-approved reporting destination first.
