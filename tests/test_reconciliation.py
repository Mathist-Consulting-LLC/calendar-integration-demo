import copy
import unittest

from calendar_demo.reconciliation import build_plan
from calendar_demo.workflow import execute


def source(source_id="source-1", **changes):
    row = {
        "source_id": source_id,
        "title": "Example",
        "description": "Fictional description.",
        "starts_at": "2026-11-10T18:00:00-07:00",
        "ends_at": "2026-11-10T19:00:00-07:00",
        "timezone": "America/Denver",
        "status": "scheduled",
    }
    row.update(changes)
    return row


def provider_row(source_id="source-1", **changes):
    row = {
        "provider_id": "provider-1",
        "source_id": source_id,
        "title": "Example",
        "description": "Fictional description.",
        "start_utc": "2026-11-11T01:00:00Z",
        "end_utc": "2026-11-11T02:00:00Z",
        "timezone": "America/Denver",
    }
    row.update(changes)
    return row


def state(rows=None, behavior=None):
    return {"destination_events": rows or [], "uncertain_operations": {}, "behavior": behavior or {}}


class ReconciliationTests(unittest.TestCase):
    def test_create_update_and_skip_decisions(self):
        events = [source("new"), source("changed"), source("same")]
        current = state([
            provider_row("changed", description="Old"),
            provider_row("same"),
        ])
        self.assertEqual([item.action for item in build_plan(events, current)], ["create", "update", "skip"])

    def test_duplicate_stable_ids_require_review(self):
        current = state([provider_row(), provider_row(provider_id="provider-2")])
        item = build_plan([source()], current)[0]
        self.assertEqual(item.action, "review")
        self.assertIn("Multiple destination", item.reason)

    def test_title_only_match_is_not_used(self):
        current = state([provider_row(source_id="different-source")])
        self.assertEqual(build_plan([source()], current)[0].action, "create")

    def test_canceled_event_never_deletes(self):
        item = build_plan([source(status="canceled")], state([provider_row()]))[0]
        self.assertEqual(item.action, "review")
        self.assertIn("never causes automatic deletion", item.reason)

    def test_dry_run_does_not_modify_state(self):
        current = state()
        before = copy.deepcopy(current)
        after, report = execute([source()], current, apply=False, approved_actions=set())
        self.assertEqual(after, before)
        self.assertEqual(report["operations"], [])

    def test_second_apply_is_idempotent(self):
        current = state()
        current, first = execute([source()], current, apply=True, approved_actions={"create", "update"})
        current, second = execute([source()], current, apply=True, approved_actions={"create", "update"})
        self.assertEqual(len(first["operations"]), 1)
        self.assertEqual(second["plan_summary"], {"skip": 1})
        self.assertEqual(second["operations"], [])
        self.assertEqual(len(current["destination_events"]), 1)

    def test_unapproved_change_is_not_written(self):
        current = state([provider_row(description="Old")])
        current, report = execute([source()], current, apply=True, approved_actions={"create"})
        self.assertEqual(report["items"][0]["outcome"], "not_approved")
        self.assertEqual(current["destination_events"][0]["description"], "Old")

    def test_provider_failure_is_reported_without_write(self):
        behavior = {"failures": {"update:source-1": "Simulated timeout"}}
        current = state([provider_row(description="Old")], behavior)
        current, report = execute([source()], current, apply=True, approved_actions={"update"})
        self.assertEqual(report["items"][0]["outcome"], "provider_error")
        self.assertEqual(current["destination_events"][0]["description"], "Old")
        self.assertEqual(report["operations"], [])

    def test_uncertain_create_blocks_blind_retry_and_duplicate(self):
        behavior = {"uncertain": {"create:source-1": "apply_then_lose_response"}}
        current = state(behavior=behavior)
        current, first = execute([source()], current, apply=True, approved_actions={"create"})
        current, second = execute([source()], current, apply=True, approved_actions={"create"})
        self.assertEqual(first["items"][0]["outcome"], "uncertain")
        self.assertEqual(second["items"][0]["action"], "review")
        self.assertEqual(second["operations"], [])
        self.assertEqual(len(current["destination_events"]), 1)


if __name__ == "__main__":
    unittest.main()
