# Publication readiness review

This repository is public at `Mathist-Consulting-LLC/calendar-integration-demo`.

The code is a fictional, credential-free, local-only demonstration. Its provider behavior is simulated; publication does not establish compatibility with any live calendar API, SDK, authentication flow, or production environment.

Checks used for public maintenance and release review:

- run the complete test suite and all example scenarios from reset state;
- run `python scripts/publication_audit.py` against the tracked files;
- inspect `git status`, `git log --oneline --decorate`, and `git show --stat`;
- confirm commit metadata contains no personal contact information;
- inspect every JSON fixture for fictional names, IDs, descriptions, and dates;
- confirm the SVG has no metadata block or embedded raster content;
- confirm `pyproject.toml` has no runtime dependencies;
- confirm generated state/report files are ignored and absent from history;
- review the README, case study, and Upwork copy for simulated-provider language;
- confirm the included MIT License and Mathist Consulting copyright notice.

The automated scan checks a bounded set of secret shapes, email addresses, absolute user paths, and SVG metadata. A clean result does not guarantee that every sensitive value is absent. Human review remains required.

## Resolved decisions

The repository uses the MIT License with a 2026 Mathist Consulting copyright notice. The implementation was newly written for this demo using Python's standard library; no production source file was copied.

Repository content and examples use fictional events and generic project attribution. Generated local state remains ignored and must not be committed.
