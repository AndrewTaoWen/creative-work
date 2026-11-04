import json
import tempfile
import unittest
from pathlib import Path

from voicebench.gate import check_gate
from voicebench.tasks import load_tasks

TASKS_DIR = Path(__file__).parent.parent / "tasks"

# Test fixtures only. None of this text is a human writing sample.
PASSING_EMAIL = (
    "Hi Priya, Thursday won't work because I have an exam that afternoon. "
    "Friday after 1pm or Monday morning would both be fine. Sam"
)


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


class GateTests(unittest.TestCase):
    def setUp(self):
        self.task = load_tasks(TASKS_DIR)["email-01-reschedule"]

    def test_passing_text(self):
        self.assertTrue(check_gate(self.task, PASSING_EMAIL).passed)

    def test_curly_apostrophe_matches(self):
        text = PASSING_EMAIL.replace("won't", "won’t")
        self.assertTrue(check_gate(self.task, text).passed)

    def test_missing_fact(self):
        result = check_gate(self.task, "Friday after 1pm works.")
        self.assertIn("monday", result.missing_facts)
        self.assertFalse(result.passed)

    def test_forbidden_claim(self):
        result = check_gate(self.task, PASSING_EMAIL + " See you Thursday!")
        self.assertIn("accepts_thursday", result.forbidden_hits)

    def test_word_limit(self):
        result = check_gate(self.task, PASSING_EMAIL + " extra" * 100)
        self.assertTrue(result.over_limit)
        self.assertFalse(result.passed)


class SampleTests(unittest.TestCase):
    def test_every_task_has_a_passing_sample(self):
        samples = json.loads(Path(__file__).with_name("gate_samples.json").read_text("utf-8"))
        samples.pop("_note")
        tasks = load_tasks(TASKS_DIR)
        self.assertEqual(set(samples), set(tasks))
        for task_id, text in samples.items():
            with self.subTest(task_id):
                result = check_gate(tasks[task_id], text)
                self.assertEqual(result.missing_facts, ())
                self.assertEqual(result.forbidden_hits, ())
                self.assertFalse(result.over_limit)


if __name__ == "__main__":
    unittest.main()
