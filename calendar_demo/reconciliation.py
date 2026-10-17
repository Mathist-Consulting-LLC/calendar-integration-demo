from __future__ import annotations

from collections import Counter
from typing import Any

from .models import MANAGED_FIELDS, PlanItem, ValidationError, map_source_event


def build_plan(source_events: list[dict[str, Any]], state: dict[str, Any]) -> list[PlanItem]:
    destination = state.get("destination_events", [])
    uncertain = state.get("uncertain_operations", {})
    source_counts = Counter(str(row.get("source_id") or "") for row in source_events)
    plan: list[PlanItem] = []

    for raw in source_events:
        source_id = str(raw.get("source_id") or "<missing>").strip() or "<missing>"
        if source_id != "<missing>" and source_counts[source_id] > 1:
            plan.append(PlanItem(source_id, "review", "Duplicate source_id appears in the source feed."))
            continue
        try:
            mapped = map_source_event(raw)
        except ValidationError as exc:
            plan.append(PlanItem(source_id, "review", f"Invalid source event: {exc}"))
            continue

        if mapped.source_id in uncertain:
            plan.append(PlanItem(
                mapped.source_id,
                "review",
                "A prior write has an uncertain outcome. Verify local provider state and clear the marker manually; no retry was attempted.",
                mapped=mapped,
            ))
            continue

        matches = [row for row in destination if str(row.get("source_id") or "") == mapped.source_id]
        if len(matches) > 1:
            plan.append(PlanItem(
                mapped.source_id,
                "review",
                "Multiple destination records share this stable source_id; no write is safe.",
                mapped=mapped,
            ))
            continue
        if mapped.status == "canceled":
            provider_id = str(matches[0].get("provider_id") or "") if matches else ""
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
                provider_id=str(existing.get("provider_id") or ""),
                changes=changes,
                mapped=mapped,
            ))
        else:
            plan.append(PlanItem(
                mapped.source_id,
                "skip",
                "Destination managed fields already match.",
                provider_id=str(existing.get("provider_id") or ""),
                mapped=mapped,
            ))
    return plan
