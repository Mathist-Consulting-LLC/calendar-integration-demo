import copy
import unittest

from calendar_demo.models import PlanItem, map_source_event
from calendar_demo.provider import ProviderError, SimulatedProvider, UncertainWriteOutcome
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
            provider_row("changed", provider_id="provider-changed", description="Old"),
            provider_row("same", provider_id="provider-same"),
        ])
        self.assertEqual([item.action for item in build_plan(events, current)], ["create", "update", "skip"])

    def test_duplicate_stable_ids_require_review(self):
        current = state([provider_row(), provider_row(provider_id="provider-2")])
        item = build_plan([source()], current)[0]
        self.assertEqual(item.action, "review")
        self.assertIn("Multiple destination", item.reason)

    def test_source_identity_is_normalized_before_duplicate_detection(self):
        items = build_plan([source(" a "), source("a")], state())
        self.assertEqual([item.action for item in items], ["review", "review"])
        self.assertEqual([item.source_id for item in items], ["a", "a"])

    def test_real_missing_word_does_not_collide_with_absent_identity(self):
        invalid = source()
        del invalid["source_id"]
        items = build_plan([source("<missing>"), invalid], state())
        self.assertEqual(items[0].action, "create")
        self.assertEqual(items[0].source_id, "<missing>")
        self.assertEqual(items[1].action, "review")
        self.assertEqual(items[1].source_id, "")

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

    def test_duplicate_provider_ids_block_all_writes_and_leave_rows_untouched(self):
        rows = [
            provider_row("source-1", provider_id="shared", description="Keep one"),
            provider_row("source-2", provider_id="shared", description="Keep two"),
        ]
        current = state(copy.deepcopy(rows))
        current, report = execute(
            [source("source-1", description="Changed")],
            current,
            apply=True,
            approved_actions={"update"},
        )
        self.assertEqual(report["items"][0]["outcome"], "review")
        self.assertIn("provider_id 'shared' is duplicated", report["items"][0]["reason"])
        self.assertEqual(current["destination_events"], rows)
        self.assertEqual(report["operations"], [])

    def test_empty_provider_id_is_a_clear_review_without_write(self):
        current = state([provider_row(provider_id=" ", description="Old")])
        current, report = execute([source(description="Changed")], current, apply=True, approved_actions={"update"})
        self.assertEqual(report["items"][0]["outcome"], "review")
        self.assertIn("empty provider_id", report["items"][0]["reason"])
        self.assertEqual(current["destination_events"][0]["description"], "Old")

    def test_provider_verifies_source_and_provider_identity_before_update(self):
        current = state([provider_row("other-source", provider_id="provider-1", description="Keep")])
        item = PlanItem(
            "source-1",
            "update",
            "test",
            provider_id="provider-1",
            mapped=map_source_event(source("source-1", description="Changed")),
        )
        with self.assertRaisesRegex(ProviderError, "source_id does not match"):
            SimulatedProvider(current).apply(item)
        self.assertEqual(current["destination_events"][0]["description"], "Keep")

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

    def test_uncertain_create_is_rechecked_before_a_later_apply_in_same_batch(self):
        behavior = {"uncertain": {"create:source-1": "apply_then_lose_response"}}
        current = state(behavior=behavior)
        item = PlanItem(
            "source-1",
            "create",
            "test",
            mapped=map_source_event(source("source-1")),
        )
        provider = SimulatedProvider(current)
        with self.assertRaises(UncertainWriteOutcome):
            provider.apply(item)
        with self.assertRaisesRegex(ProviderError, "unresolved write outcome"):
            provider.apply(item)
        self.assertEqual(len(current["destination_events"]), 1)
        self.assertEqual(len(provider.operations), 1)


if __name__ == "__main__":
    unittest.main()
