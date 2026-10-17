# Upwork portfolio copy

## Title

Dry-Run-First Calendar API Reconciliation Demo

## Description

I built this self-initiated backend demonstration to show how I approach small integration projects where duplicate writes and unclear ownership are the real risks.

The command-line workflow reads fictional calendar events and simulated destination state, validates timezones and required fields, and produces a create, update, skip, or review plan. Dry-run is the default. An explicit apply command can change only local simulated state, and a second run proves that unchanged events do not create duplicate writes.

The demo also covers ambiguous matches, invalid data, cancellations, provider failures, and an uncertain create outcome that is held for review instead of blindly retried. Automated tests verify mapping, decision logic, idempotency, timezone handling, and reset safety.

All provider behavior is simulated. The repository uses no credentials, external services, real event data, or frontend. It is designed as a bounded implementation example with a clear written handoff.
