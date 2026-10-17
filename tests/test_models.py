import unittest

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


if __name__ == "__main__":
    unittest.main()
