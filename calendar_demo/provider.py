from __future__ import annotations

import hashlib
from typing import Any

from .models import PlanItem


class ProviderError(RuntimeError):
    pass


class UncertainWriteOutcome(ProviderError):
    pass


class SimulatedProvider:
    """Local adapter boundary. It never performs network I/O."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state
        self.operations: list[dict[str, str]] = []

    def apply(self, item: PlanItem) -> None:
        if item.action not in {"create", "update"} or item.mapped is None:
            raise ValueError("provider can apply only mapped create/update items")
        key = f"{item.action}:{item.source_id}"
        behavior = self.state.get("behavior", {})
        failures = behavior.get("failures", {})
        if key in failures:
            raise ProviderError(str(failures[key]))

        if item.action == "create":
            provider_id = _provider_id(item.source_id)
            row = {"provider_id": provider_id, **item.mapped.provider_fields(), "source_id": item.source_id}
            self.state.setdefault("destination_events", []).append(row)
        else:
            row = next(
                record for record in self.state.setdefault("destination_events", [])
                if record.get("provider_id") == item.provider_id
            )
            row.update(item.mapped.provider_fields())
            provider_id = item.provider_id

        self.operations.append({"action": item.action, "source_id": item.source_id, "provider_id": provider_id})
        uncertain = behavior.get("uncertain", {})
        if key in uncertain:
            self.state.setdefault("uncertain_operations", {})[item.source_id] = {
                "operation": item.action,
                "provider_id": provider_id,
                "simulation": str(uncertain[key]),
            }
            raise UncertainWriteOutcome(
                "The simulated provider may have accepted the write, but the response was lost. Blind retry is blocked."
            )


def _provider_id(source_id: str) -> str:
    return "sim-" + hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:12]
