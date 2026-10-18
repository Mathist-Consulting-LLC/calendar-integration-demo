import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfoNotFoundError

from calendar_demo.models import ValidationError, map_source_event


def event(**changes):
    row = {
        "source_id": "source-1",
        "title": "Example",
        "description": "Fictional description.",
        "starts_at": "2026-11-10T18:00:00-07:00",
        "ends_at": "2026-11-10T19:00:00-07:00",
        "timezone": "America/Denver",
        "status": "scheduled",
    }
    row.update(changes)
    return row


class MappingTests(unittest.TestCase):
    def test_maps_explicit_timezone_to_utc(self):
        mapped = map_source_event(event())
        self.assertEqual(mapped.start_utc, "2026-11-11T01:00:00Z")
        self.assertEqual(mapped.timezone, "America/Denver")

    def test_rejects_offset_that_disagrees_with_timezone(self):
        with self.assertRaisesRegex(ValidationError, "offset does not match"):
            map_source_event(event(starts_at="2026-11-10T18:00:00-06:00"))

    def test_rejects_missing_description_instead_of_erasing_destination_copy(self):
        row = event()
        del row["description"]
        with self.assertRaisesRegex(ValidationError, "description is required"):
            map_source_event(row)

    def test_rejects_inverted_time_range(self):
        with self.assertRaisesRegex(ValidationError, "after"):
            map_source_event(event(ends_at="2026-11-10T17:00:00-07:00"))

    def test_accepts_denver_daylight_time_offset(self):
        mapped = map_source_event(event(
            starts_at="2026-06-10T18:00:00-06:00",
            ends_at="2026-06-10T19:00:00-06:00",
        ))
        self.assertEqual(mapped.start_utc, "2026-06-11T00:00:00Z")

    def test_rejects_nonexistent_denver_spring_forward_hour(self):
        with self.assertRaisesRegex(ValidationError, "nonexistent"):
            map_source_event(event(
                starts_at="2026-03-08T02:30:00-07:00",
                ends_at="2026-03-08T04:00:00-06:00",
            ))

    def test_fallback_rejects_spring_forward_gap(self):
        with patch("calendar_demo.models.ZoneInfo", side_effect=ZoneInfoNotFoundError("forced fallback")):
            with self.assertRaisesRegex(ValidationError, "nonexistent"):
                map_source_event(event(
                    starts_at="2026-03-08T02:30:00-07:00",
                    ends_at="2026-03-08T04:00:00-06:00",
                ))

    def test_fall_back_hour_accepts_each_explicit_offset(self):
        for offset in ("-06:00", "-07:00"):
            with self.subTest(offset=offset):
                mapped = map_source_event(event(
                    starts_at=f"2026-11-01T01:15:00{offset}",
                    ends_at=f"2026-11-01T01:45:00{offset}",
                ))
                self.assertLess(mapped.start_utc, mapped.end_utc)

    def test_fallback_fall_back_hour_accepts_each_explicit_offset(self):
        with patch("calendar_demo.models.ZoneInfo", side_effect=ZoneInfoNotFoundError("forced fallback")):
            self.test_fall_back_hour_accepts_each_explicit_offset()

    def test_fallback_rejects_offset_mismatch(self):
        with patch("calendar_demo.models.ZoneInfo", side_effect=ZoneInfoNotFoundError("forced fallback")):
            with self.assertRaisesRegex(ValidationError, "offset does not match"):
                map_source_event(event(starts_at="2026-11-10T18:00:00-06:00"))

    def test_malformed_timezone_keys_are_controlled_validation_errors(self):
        for key in ("/etc/passwd", "../America/Denver", "America\\Denver"):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValidationError, "unknown timezone"):
                    map_source_event(event(timezone=key))

    def test_fractional_second_interval_preserves_positive_duration(self):
        mapped = map_source_event(event(
            starts_at="2026-11-10T18:00:00.100000-07:00",
            ends_at="2026-11-10T18:00:00.900000-07:00",
        ))
        self.assertEqual(mapped.start_utc, "2026-11-11T01:00:00.100000Z")
        self.assertEqual(mapped.end_utc, "2026-11-11T01:00:00.900000Z")
        self.assertNotEqual(mapped.start_utc, mapped.end_utc)

    def test_denver_fallback_rejects_years_outside_supported_range(self):
        with patch("calendar_demo.models.ZoneInfo", side_effect=ZoneInfoNotFoundError("forced fallback")):
            for year in (1900, 2038):
                with self.subTest(year=year):
                    with self.assertRaisesRegex(ValidationError, "supports years 2007-2037"):
                        map_source_event(event(
                            starts_at=f"{year}-06-10T18:00:00-06:00",
                            ends_at=f"{year}-06-10T19:00:00-06:00",
                        ))


if __name__ == "__main__":
    unittest.main()
