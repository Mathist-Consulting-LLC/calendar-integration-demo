from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .provider import ProviderError, SimulatedProvider, UncertainWriteOutcome
from .reconciliation import build_plan


def execute(
    source_events: list[dict[str, Any]],
    state: dict[str, Any],
    *,
    apply: bool,
    approved_actions: set[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = build_plan(source_events, state)
    provider = SimulatedProvider(state)
    results: list[dict[str, Any]] = []

    for item in plan:
        row = item.public_dict()
        row["outcome"] = "planned" if not apply else "not_applied"
        if not apply or item.action not in {"create", "update"}:
            if apply and item.action in {"skip", "review"}:
                row["outcome"] = item.action
            results.append(row)
            continue
        if item.action not in approved_actions:
            row["outcome"] = "not_approved"
            results.append(row)
            continue
        try:
            provider.apply(item)
            row["outcome"] = "applied"
        except UncertainWriteOutcome as exc:
            row["outcome"] = "uncertain"
            row["reason"] = str(exc)
        except ProviderError as exc:
            row["outcome"] = "provider_error"
            row["reason"] = str(exc)
        results.append(row)

    report = {
        "mode": "apply" if apply else "dry-run",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "plan_summary": dict(sorted(Counter(item.action for item in plan).items())),
        "outcome_summary": dict(sorted(Counter(row["outcome"] for row in results).items())),
        "operations": provider.operations,
        "items": results,
    }
    return state, report
