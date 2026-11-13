import csv
import json
import tempfile
import unittest
from pathlib import Path

from voicebench.cli import main
from voicebench.gate import check_gate
from voicebench.panel import KEY_NAME, SHEET_NAME, build_packet
from voicebench.runs import Output, load_run
from voicebench.scoring import load_baselines, score_output
from voicebench.style import Baseline
from voicebench.tasks import load_tasks, select_split
from voicebench.tells import tell_counts, tell_rate

TASKS_DIR = Path(__file__).parent.parent / "tasks"

# Test fixtures only. None of this text is a human writing sample.
PASSING_EMAIL = (
    "Hi Priya, Thursday won't work because I have an exam that afternoon. "
    "Friday after 1pm or Monday morning would both be fine. Sam"
)
TELL_HEAVY_EMAIL = (
    "I hope this email finds you well. Moreover, this is not just a date change but a "
    "testament to my commitment. **Friday** works.\n- Monday\n"
    "Please don't hesitate to reach out."
)


def raw_task(task_id="x", kind="email", split="dev"):
    return {
        "id": task_id, "kind": kind, "split": split, "title": "t", "persona": "p",
        "context": "c", "instruction": "i", "max_words": 10, "forbidden": [],
        "required_facts": [{"id": "a", "description": "d", "any_of": ["x"]}],
    }


def load_raw(*raws):
    with tempfile.TemporaryDirectory() as folder:
        Path(folder, "tasks.json").write_text(json.dumps(list(raws)))
        return load_tasks(Path(folder))


class TaskTests(unittest.TestCase):
    def test_seed_tasks_load(self):
        tasks = load_tasks(TASKS_DIR)
        self.assertEqual(sum(t.kind == "email" for t in tasks.values()), 15)
        self.assertEqual(sum(t.kind == "takehome" for t in tasks.values()), 5)

    def test_rejects_bad_kind(self):
        with self.assertRaisesRegex(ValueError, "unknown kind"):
            load_raw(raw_task(kind="poem"))

    def test_rejects_bad_split(self):
        with self.assertRaisesRegex(ValueError, "unknown split"):
            load_raw(raw_task(split="test"))

    def test_select_split(self):
        tasks = load_raw(raw_task("a"), raw_task("b", split="heldout"))
        self.assertEqual(set(select_split(tasks, "dev")), {"a"})
        self.assertEqual(set(select_split(tasks, "heldout")), {"b"})
        self.assertEqual(set(select_split(tasks, None)), {"a", "b"})

    def test_select_split_rejects_empty(self):
        with self.assertRaisesRegex(ValueError, "no tasks in split"):
            select_split(load_raw(raw_task()), "heldout")


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


class TellTests(unittest.TestCase):
    def test_finds_each_category(self):
        counts = tell_counts(TELL_HEAVY_EMAIL, "email")
        for name in ("negative_parallelism", "pet_words", "stock_phrases",
                     "inflated_significance", "email_markup"):
            self.assertGreater(counts[name], 0, name)

    def test_markup_only_counts_in_email(self):
        self.assertNotIn("email_markup", tell_counts("# Title", "takehome"))

    def test_clean_text_has_no_tells(self):
        self.assertEqual(tell_rate(PASSING_EMAIL, "email"), 0)

    def test_empty_text(self):
        self.assertEqual(tell_rate("", "email"), 0)


class StyleTests(unittest.TestCase):
    def test_needs_enough_texts(self):
        with self.assertRaisesRegex(ValueError, "at least"):
            Baseline(["one", "two"])

    def test_closer_text_scores_lower(self):
        baseline = Baseline([
            "I can't make it. Sorry about that.",
            "We're out Friday. I'll call you.",
            "I didn't see this. Can we talk?",
            "That's fine by me. Thanks.",
            "I'm around Monday. Let's chat then.",
        ])
        similar = "I can't do Friday. We'll chat Monday."
        different = (
            "The implementation of organizational documentation requirements "
            "necessitates comprehensive consideration of operational functionality."
        )
        self.assertLess(baseline.distance(similar), baseline.distance(different))


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tasks = load_tasks(TASKS_DIR)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.run_dir = Path(self.folder.name, "run")
        for condition, text in (("plain", PASSING_EMAIL), ("stock", TELL_HEAVY_EMAIL)):
            path = self.run_dir / condition / "email-01-reschedule.txt"
            path.parent.mkdir(parents=True)
            path.write_text(text, encoding="utf-8")

    def test_rejects_unknown_task(self):
        path = self.run_dir / "plain" / "nope.txt"
        path.write_text("hello", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "no task named"):
            load_run(self.run_dir, self.tasks)

    def test_rejects_empty_output(self):
        path = self.run_dir / "plain" / "email-02-slip.txt"
        path.write_text("  ", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "empty"):
            load_run(self.run_dir, self.tasks)

    def test_score_command(self):
        code = main(["--tasks", str(TASKS_DIR), "score", str(self.run_dir)])
        self.assertEqual(code, 0)
        with (self.run_dir / "scores.csv").open(encoding="utf-8") as file:
            rows = {row["condition"]: row for row in csv.DictReader(file)}
        self.assertEqual(rows["plain"]["gate_passed"], "True")
        self.assertEqual(rows["stock"]["gate_passed"], "False")
        self.assertEqual(float(rows["plain"]["tell_rate"]), 0)
        self.assertGreater(float(rows["stock"]["tell_rate"]), 0)
        self.assertEqual(rows["plain"]["style_distance"], "")
        self.assertEqual(rows["plain"]["split"], "dev")

    def test_score_split_leaves_out_other_tasks(self):
        raw = json.loads((TASKS_DIR / "email.json").read_text("utf-8"))
        for task in raw:
            if task["id"] == "email-02-slip":
                task["split"] = "heldout"
        tasks_dir = Path(self.folder.name, "tasks")
        tasks_dir.mkdir()
        (tasks_dir / "email.json").write_text(json.dumps(raw), encoding="utf-8")
        (self.run_dir / "plain" / "email-02-slip.txt").write_text("Nov 21.", encoding="utf-8")
        code = main(["--tasks", str(tasks_dir), "--split", "heldout", "score", str(self.run_dir)])
        self.assertEqual(code, 0)
        with (self.run_dir / "scores.csv").open(encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual([(row["task_id"], row["split"]) for row in rows],
                         [("email-02-slip", "heldout")])

    def test_style_distance_uses_matching_kind(self):
        human = Path(self.folder.name, "human", "email")
        human.mkdir(parents=True)
        for index in range(5):
            (human / f"{index}.txt").write_text(f"I can't today. Sorry {index}.")
        output = Output("plain", self.tasks["email-01-reschedule"], PASSING_EMAIL)
        row = score_output(output, load_baselines(human.parent))
        self.assertNotEqual(row["style_distance"], "")

    def test_panel_hides_condition_and_gates_failures(self):
        outputs = load_run(self.run_dir, self.tasks)
        out = Path(self.folder.name, "panel")
        self.assertEqual(build_packet(outputs, out, seed=1), 1)
        sheet = (out / SHEET_NAME).read_text(encoding="utf-8")
        with (out / KEY_NAME).open(encoding="utf-8") as file:
            key = list(csv.DictReader(file))
        self.assertEqual([row["condition"] for row in key], ["plain"])
        self.assertNotIn("plain", sheet.lower().split("\n")[0])
        self.assertNotIn("condition", sheet)
        self.assertNotIn("email-01", sheet)

    def test_panel_can_include_failures(self):
        outputs = load_run(self.run_dir, self.tasks)
        out = Path(self.folder.name, "panel")
        self.assertEqual(build_packet(outputs, out, seed=1, include_failed=True), 2)


if __name__ == "__main__":
    unittest.main()
