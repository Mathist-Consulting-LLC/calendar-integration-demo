# Design notes

## Source of truth and stable identity

The fictional source feed is authoritative for the managed event fields. Every event must have a stable `source_id`; whitespace is trimmed once and that canonical value is used for validation, duplicate detection, planning, uncertainty markers, and applying. Missing identity is represented by `None`, not by a collidable string sentinel. Destination records are matched only on the canonical ID. A shared title is not treated as identity. Zero matches plan a create, one match can update or skip, and multiple matches stop for review.

## Idempotency

The workflow compares a normalized, timezone-aware source event with simulated destination state before writing. It repeats identity and unresolved-write checks immediately before every mutation. Successful creates persist the stable source ID. A repeat run therefore sees the record and plans `skip` instead of another create. Updates modify only the managed field allowlist.

## Validation and cancellation

Title, description, start, end, timezone, status, and stable ID are required. Timestamps must include an offset consistent with the named IANA timezone. Invalid or missing data becomes `review`; it cannot erase destination values. Canceled events also become `review` in this bounded demo. There is intentionally no automatic delete operation.

Destination source and provider IDs are validated before mutation. Empty IDs or duplicate provider IDs block writes for review, and an update must match exactly one record by provider ID and the same canonical source ID.

UTC output preserves fractional seconds. When system IANA data is unavailable, the built-in `America/Denver` fallback supports 2007-2037 only; this is the bounded period for which its modern U.S. daylight-saving rules are intentional. Denver dates outside that range require system IANA data.

## Uncertain outcomes

Non-idempotent writes can succeed remotely even when the caller loses the response. The simulated adapter can apply a create and then raise an uncertain-outcome error. It persists an uncertainty marker before the next run. Later runs stop for review rather than blindly creating again.

## Adapter boundary

`SimulatedProvider` is the only mutation boundary. It operates on local JSON and contains no HTTP client, credentials, SDK, or provider-specific claim. The planner and mapper are provider-neutral, so a real adapter could be added later only with a separately reviewed API contract, authentication design, and non-production proof.
