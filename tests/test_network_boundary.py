import unittest
from unittest.mock import patch

from calendar_demo.workflow import execute


class NetworkBoundaryTests(unittest.TestCase):
    def test_workflow_completes_when_network_connections_are_forbidden(self):
        event = {
            "source_id": "offline-1",
            "title": "Offline Example",
            "description": "Fictional event.",
            "starts_at": "2026-11-10T18:00:00-07:00",
            "ends_at": "2026-11-10T19:00:00-07:00",
            "timezone": "America/Denver",
            "status": "scheduled",
        }
        state = {"destination_events": [], "uncertain_operations": {}, "behavior": {}}
        with patch("socket.create_connection", side_effect=AssertionError("network access attempted")):
            _, report = execute([event], state, apply=True, approved_actions={"create"})
        self.assertEqual(report["outcome_summary"], {"applied": 1})


if __name__ == "__main__":
    unittest.main()
