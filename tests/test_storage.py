import unittest
from pathlib import Path
from unittest.mock import patch

from calendar_demo import storage


class StorageTests(unittest.TestCase):
    def test_guard_rejects_unrelated_path(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            storage._assert_generated_file(Path(__file__))

    def test_reset_removes_only_known_generated_json_files(self):
        generated = Path(__file__).parent / ".tmp-reset"
        generated.mkdir(exist_ok=True)
        try:
            expected = generated / "portfolio-state.json"
            unrelated = generated / "keep-me.txt"
            expected.write_text("{}", encoding="utf-8")
            unrelated.write_text("keep", encoding="utf-8")
            with patch.object(storage, "GENERATED", generated):
                removed = storage.reset_generated()
            self.assertEqual(len(removed), 1)
            self.assertFalse(expected.exists())
            self.assertTrue(unrelated.exists())
        finally:
            for path in (generated / "portfolio-state.json", generated / "keep-me.txt"):
                if path.exists():
                    path.unlink()
            generated.rmdir()


if __name__ == "__main__":
    unittest.main()
