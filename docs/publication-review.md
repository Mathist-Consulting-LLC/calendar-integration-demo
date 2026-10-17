# Publication readiness review

This repository is prepared for review, not publication.

Checks to run before making it public:

- run the complete test suite and all example scenarios from reset state;
- run `python scripts/publication_audit.py` against the tracked files;
- inspect `git status`, `git log --oneline --decorate`, and `git show --stat`;
- confirm the generic project commit identity is appropriate for publication;
- inspect every JSON fixture for fictional names, IDs, descriptions, and dates;
- confirm the SVG has no metadata block or embedded raster content;
- confirm `pyproject.toml` has no runtime dependencies;
- confirm generated state/report files are ignored and absent from history;
- review the README, case study, and Upwork copy for simulated-provider language;
- confirm the included MIT License and Mathist Consulting copyright notice.

The automated scan checks a bounded set of secret shapes, email addresses, absolute user paths, and SVG metadata. A clean result does not guarantee that every sensitive value is absent. Human review remains required.

## Resolved decisions

The repository uses the MIT License with a 2026 Mathist Consulting copyright notice. The implementation was newly written for this demo using Python's standard library; no production source file was copied.

The local commit uses the generic project identity `Calendar Integration Demo <calendar-integration-demo@localhost>`. It contains no personal name or personal contact information.
