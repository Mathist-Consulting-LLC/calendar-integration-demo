from __future__ import annotations

import hashlib
from typing import Any

from .models import PlanItem, canonical_source_id
from .reconciliation import validate_destination_identities


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
        source_id = canonical_source_id(item.source_id)
        mapped_source_id = canonical_source_id(item.mapped.source_id)
        if source_id is None or mapped_source_id != source_id:
            raise ProviderError("Source identity changed or is invalid; no write was attempted.")

        destination = self.state.setdefault("destination_events", [])
        identity_errors = validate_destination_identities(destination)
        if identity_errors:
            raise ProviderError("Destination identity validation failed: " + "; ".join(identity_errors))

        uncertain_ids = {
            identity
            for value in self.state.get("uncertain_operations", {})
            if (identity := canonical_source_id(value)) is not None
        }
        if source_id in uncertain_ids:
            raise ProviderError("This source_id has an unresolved write outcome; no retry was attempted.")

        key = f"{item.action}:{source_id}"
        behavior = self.state.get("behavior", {})
        failures = behavior.get("failures", {})
        if key in failures:
            raise ProviderError(str(failures[key]))

        if item.action == "create":
            matches = [
                record for record in destination
                if canonical_source_id(record.get("source_id")) == source_id
            ]
            if matches:
                raise ProviderError("Destination state already contains this source_id; no create was attempted.")
            provider_id = _provider_id(source_id)
            if any(_canonical_provider_id(record.get("provider_id")) == provider_id for record in destination):
                raise ProviderError("Generated provider_id collides with destination state; no create was attempted.")
            row = {"provider_id": provider_id, **item.mapped.provider_fields(), "source_id": source_id}
            destination.append(row)
        else:
            provider_id = _canonical_provider_id(item.provider_id)
            if provider_id is None:
                raise ProviderError("Update requires a non-empty provider_id; no write was attempted.")
            matches = [
                record for record in destination
                if _canonical_provider_id(record.get("provider_id")) == provider_id
            ]
            if len(matches) != 1:
                raise ProviderError("Update provider_id is missing or ambiguous; no write was attempted.")
            row = matches[0]
            if canonical_source_id(row.get("source_id")) != source_id:
                raise ProviderError("Update source_id does not match the provider record; no write was attempted.")
            row.update(item.mapped.provider_fields())

        self.operations.append({"action": item.action, "source_id": source_id, "provider_id": provider_id})
        uncertain = behavior.get("uncertain", {})
        if key in uncertain:
            self.state.setdefault("uncertain_operations", {})[source_id] = {
                "operation": item.action,
                "provider_id": provider_id,
                "simulation": str(uncertain[key]),
            }
            raise UncertainWriteOutcome(
                "The simulated provider may have accepted the write, but the response was lost. Blind retry is blocked."
            )


def _provider_id(source_id: str) -> str:
    return "sim-" + hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:12]


def _canonical_provider_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None
