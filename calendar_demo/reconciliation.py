from __future__ import annotations

from collections import Counter
from typing import Any

from .models import (
    MANAGED_FIELDS,
    PlanItem,
    ValidationError,
    canonical_source_id,
    map_source_event,
)


def build_plan(source_events: list[dict[str, Any]], state: dict[str, Any]) -> list[PlanItem]:
    destination = state.get("destination_events", [])
    uncertain = state.get("uncertain_operations", {})
    source_identities = [canonical_source_id(row.get("source_id")) for row in source_events]
    source_counts = Counter(identity for identity in source_identities if identity is not None)
    uncertain_identities = {
        identity
        for value in uncertain
        if (identity := canonical_source_id(value)) is not None
    }
    destination_errors = validate_destination_identities(destination)
    plan: list[PlanItem] = []

    for raw, source_id in zip(source_events, source_identities):
        display_id = source_id or ""
        if source_id is not None and source_counts[source_id] > 1:
            plan.append(PlanItem(source_id, "review", "Duplicate source_id appears in the source feed."))
            continue
        try:
            mapped = map_source_event(raw)
        except ValidationError as exc:
            plan.append(PlanItem(display_id, "review", f"Invalid source event: {exc}"))
            continue

        if destination_errors:
            plan.append(PlanItem(
                mapped.source_id,
                "review",
                "Destination identity validation failed: " + "; ".join(destination_errors),
                mapped=mapped,
            ))
            continue

        if mapped.source_id in uncertain_identities:
            plan.append(PlanItem(
                mapped.source_id,
                "review",
                "A prior write has an uncertain outcome. Verify local provider state and clear the marker manually; no retry was attempted.",
                mapped=mapped,
            ))
            continue

        matches = [row for row in destination if canonical_source_id(row.get("source_id")) == mapped.source_id]
        if len(matches) > 1:
            plan.append(PlanItem(
                mapped.source_id,
                "review",
                "Multiple destination records share this stable source_id; no write is safe.",
                mapped=mapped,
            ))
            continue
        if mapped.status == "canceled":
            provider_id = _canonical_text(matches[0].get("provider_id")) or "" if matches else ""
            plan.append(PlanItem(
                mapped.source_id,
                "review",
                "Canceled events require human review in this demo; missing data never causes automatic deletion.",
                provider_id=provider_id,
                mapped=mapped,
            ))
            continue
        if not matches:
            plan.append(PlanItem(mapped.source_id, "create", "No destination record has this stable source_id.", mapped=mapped))
            continue

        existing = matches[0]
        changes = tuple(name for name in MANAGED_FIELDS if existing.get(name) != getattr(mapped, name))
        if changes:
            plan.append(PlanItem(
                mapped.source_id,
                "update",
                "Managed fields differ from destination state.",
                provider_id=_canonical_text(existing.get("provider_id")) or "",
                changes=changes,
                mapped=mapped,
            ))
        else:
            plan.append(PlanItem(
                mapped.source_id,
                "skip",
                "Destination managed fields already match.",
                provider_id=_canonical_text(existing.get("provider_id")) or "",
                mapped=mapped,
            ))
    return plan


def validate_destination_identities(destination: Any) -> list[str]:
    """Return deterministic safety errors before any destination mutation is planned."""
    if not isinstance(destination, list):
        return ["destination_events must be a list"]

    errors: list[str] = []
    provider_ids: list[str] = []
    for index, row in enumerate(destination):
        if not isinstance(row, dict):
            errors.append(f"destination_events[{index}] must be an object")
            continue
        if canonical_source_id(row.get("source_id")) is None:
            errors.append(f"destination_events[{index}] has an empty source_id")
        provider_id = _canonical_text(row.get("provider_id"))
        if provider_id is None:
            errors.append(f"destination_events[{index}] has an empty provider_id")
        else:
            provider_ids.append(provider_id)

    duplicates = sorted(provider_id for provider_id, count in Counter(provider_ids).items() if count > 1)
    errors.extend(f"provider_id {provider_id!r} is duplicated" for provider_id in duplicates)
    return errors


def _canonical_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None
