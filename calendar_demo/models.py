from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


MANAGED_FIELDS = ("title", "description", "start_utc", "end_utc", "timezone")
DENVER_FALLBACK_MIN_YEAR = 2007
DENVER_FALLBACK_MAX_YEAR = 2037


@dataclass(frozen=True)
class MappedEvent:
    source_id: str
    title: str
    description: str
    start_utc: str
    end_utc: str
    timezone: str
    status: str

    def provider_fields(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in MANAGED_FIELDS}


@dataclass(frozen=True)
class PlanItem:
    source_id: str
    action: str
    reason: str
    provider_id: str = ""
    changes: tuple[str, ...] = ()
    mapped: MappedEvent | None = field(default=None, repr=False)

    def public_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result.pop("mapped", None)
        result["changes"] = list(self.changes)
        return result


class ValidationError(ValueError):
    pass


def canonical_source_id(value: Any) -> str | None:
    """Return the one source identity representation used throughout the demo."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def map_source_event(raw: dict[str, Any]) -> MappedEvent:
    source_id = canonical_source_id(raw.get("source_id"))
    if source_id is None:
        raise ValidationError("source_id is required")
    title = _required_text(raw, "title")
    description = _required_text(raw, "description")
    timezone_name = _required_text(raw, "timezone")
    status = _required_text(raw, "status").lower()
    if status not in {"scheduled", "canceled"}:
        raise ValidationError("status must be 'scheduled' or 'canceled'")

    starts = _parse_timestamp(raw.get("starts_at"), "starts_at")
    ends = _parse_timestamp(raw.get("ends_at"), "ends_at")
    _require_matching_offset(starts, timezone_name, "starts_at")
    _require_matching_offset(ends, timezone_name, "ends_at")
    if ends <= starts:
        raise ValidationError("ends_at must be after starts_at")

    return MappedEvent(
        source_id=source_id,
        title=title,
        description=description,
        start_utc=_utc_string(starts),
        end_utc=_utc_string(ends),
        timezone=timezone_name,
        status=status,
    )


def _required_text(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} is required")
    return value.strip()


def _parse_timestamp(value: Any, key: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{key} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"{key} must include a UTC offset")
    return parsed


def _require_matching_offset(value: datetime, timezone_name: str, key: str) -> None:
    expected = _valid_offsets(value, timezone_name, key)
    if value.utcoffset() not in expected:
        raise ValidationError(f"{key} offset does not match the declared timezone")


def _valid_offsets(value: datetime, timezone_name: str, key: str) -> set[timedelta]:
    try:
        event_zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        return _fallback_offsets(value, timezone_name, key)

    local = value.replace(tzinfo=None)
    offsets: set[timedelta] = set()
    for fold in (0, 1):
        candidate = local.replace(tzinfo=event_zone, fold=fold)
        round_trip = candidate.astimezone(timezone.utc).astimezone(event_zone)
        if round_trip.replace(tzinfo=None) == local:
            offset = candidate.utcoffset()
            if offset is not None:
                offsets.add(offset)
    if not offsets:
        raise ValidationError(f"{key} falls in a nonexistent local hour during the DST transition")
    return offsets


def _fallback_offsets(value: datetime, timezone_name: str, key: str) -> set[timedelta]:
    if timezone_name == "UTC":
        return {timedelta(0)}
    if timezone_name != "America/Denver":
        raise ValidationError(
            f"unknown timezone without a system IANA database: {timezone_name}; "
            "this portable demo supports America/Denver and UTC"
        )
    local = value.replace(tzinfo=None)
    if not DENVER_FALLBACK_MIN_YEAR <= local.year <= DENVER_FALLBACK_MAX_YEAR:
        raise ValidationError(
            "America/Denver fallback supports years "
            f"{DENVER_FALLBACK_MIN_YEAR}-{DENVER_FALLBACK_MAX_YEAR}; "
            "install system IANA timezone data for historical dates"
        )
    march_first = datetime(local.year, 3, 1)
    november_first = datetime(local.year, 11, 1)
    dst_start_day = 8 + ((6 - march_first.weekday()) % 7)
    dst_end_day = 1 + ((6 - november_first.weekday()) % 7)
    dst_start = datetime(local.year, 3, dst_start_day, 2)
    dst_end = datetime(local.year, 11, dst_end_day, 2)
    if dst_start <= local < dst_start + timedelta(hours=1):
        raise ValidationError(f"{key} falls in a nonexistent local hour during the DST transition")
    if dst_end - timedelta(hours=1) <= local < dst_end:
        return {timedelta(hours=-6), timedelta(hours=-7)}
    if dst_start + timedelta(hours=1) <= local < dst_end - timedelta(hours=1):
        return {timedelta(hours=-6)}
    return {timedelta(hours=-7)}


def _utc_string(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
