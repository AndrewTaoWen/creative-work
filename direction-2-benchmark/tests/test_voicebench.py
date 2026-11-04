import json
import tempfile
import unittest
from pathlib import Path

from voicebench.tasks import load_tasks

TASKS_DIR = Path(__file__).parent.parent / "tasks"


class TaskTests(unittest.TestCase):
    def test_seed_tasks_load(self):
        tasks = load_tasks(TASKS_DIR)
        self.assertEqual(sum(t.kind == "email" for t in tasks.values()), 5)
        self.assertEqual(sum(t.kind == "takehome" for t in tasks.values()), 5)

    def test_rejects_bad_kind(self):
        raw = {
            "id": "x", "kind": "poem", "title": "t", "persona": "p", "context": "c",
            "instruction": "i", "max_words": 10, "forbidden": [],
            "required_facts": [{"id": "a", "description": "d", "any_of": ["x"]}],
        }
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "bad.json").write_text(json.dumps([raw]))
            with self.assertRaisesRegex(ValueError, "unknown kind"):
                load_tasks(Path(folder))


if __name__ == "__main__":
    unittest.main()
