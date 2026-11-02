import json
import tempfile
import unittest
from pathlib import Path

from voicebench.cli import main
from voicebench.experiment import Condition, load_experiment
from voicebench.generate import MANIFEST_NAME, count_calls, plan_jobs, run_jobs, select_draft
from voicebench.prompts import build_system, load_examples
from voicebench.providers import FatalGenerationError, GenerationError, Reply
from voicebench.runs import load_run
from voicebench.tasks import load_tasks

ROOT = Path(__file__).parent.parent
TASKS_DIR = ROOT / "tasks"
PLAIN = Condition("plain", "claude", "m", "medium", "plain")
DRAFTS = Condition("drafts", "claude", "m", "medium", "plain", drafts=3)


class FakeProvider:
    def __init__(self, texts=("A reply.",), fail_on=()):
        self.texts = list(texts)
        self.fail_on = set(fail_on)
        self.calls = 0

    def generate(self, request):
        index = self.calls
        self.calls += 1
        if index in self.fail_on:
            raise GenerationError("boom")
        return Reply(self.texts[index % len(self.texts)], 10, 20, request.model)


class ExperimentTests(unittest.TestCase):
    def _load(self, *conditions):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "e.json")
            path.write_text(json.dumps({"conditions": list(conditions)}))
            return load_experiment(path)

    def test_first_experiment_loads(self):
        conditions = load_experiment(ROOT / "experiments" / "first.json")
        self.assertEqual(len(conditions), 7)

    def test_rejects_temperature_on_claude(self):
        raw = {"id": "x", "provider": "claude", "model": "m", "effort": "medium",
               "prompt": "plain", "temperature": 0.5}
        with self.assertRaisesRegex(ValueError, "temperature"):
            self._load(raw)

    def test_rejects_temperature_with_reasoning(self):
        raw = {"id": "x", "provider": "openai", "model": "m", "effort": "low",
               "prompt": "plain", "temperature": 0.5}
        with self.assertRaisesRegex(ValueError, "temperature"):
            self._load(raw)

    def test_rejects_unsafe_id(self):
        raw = {"id": "../x", "provider": "claude", "model": "m", "effort": "medium",
               "prompt": "plain"}
        with self.assertRaisesRegex(ValueError, "id can only"):
            self._load(raw)


class PromptTests(unittest.TestCase):
    def test_few_shot_needs_examples(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "few_shot needs 5"):
                load_examples(Path(folder), "email")

    def test_examples_appear_in_system(self):
        system = build_system("few_shot", ["sample one", "sample two"])
        self.assertIn("sample one", system)
        self.assertIn("sample two", system)

    def test_examples_stay_out_of_baseline_files(self):
        from voicebench.scoring import load_baselines
        with tempfile.TemporaryDirectory() as folder:
            examples = Path(folder, "email", "examples")
            examples.mkdir(parents=True)
            for index in range(5):
                (examples / f"{index}.txt").write_text("text")
            self.assertEqual(load_baselines(Path(folder)), {})


class RunnerTests(unittest.TestCase):
    def setUp(self):
        tasks = load_tasks(TASKS_DIR)
        self.tasks = {"email-01-reschedule": tasks["email-01-reschedule"],
                      "email-02-slip": tasks["email-02-slip"]}
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.run_dir = Path(self.folder.name, "run")

    def test_outputs_can_be_scored(self):
        provider = FakeProvider()
        jobs = plan_jobs([PLAIN], self.tasks)
        self.assertEqual(run_jobs(jobs, {"claude": provider}, self.run_dir), [])
        self.assertEqual(len(load_run(self.run_dir, self.tasks)), 2)

    def test_rerun_makes_no_calls(self):
        provider = FakeProvider()
        jobs = plan_jobs([PLAIN, DRAFTS], self.tasks)
        run_jobs(jobs, {"claude": provider}, self.run_dir)
        self.assertEqual(provider.calls, 8)
        self.assertEqual(count_calls(jobs, self.run_dir), 0)
        run_jobs(jobs, {"claude": provider}, self.run_dir)
        self.assertEqual(provider.calls, 8)

    def test_failed_job_resumes_only_what_is_missing(self):
        jobs = plan_jobs([DRAFTS], {"email-01-reschedule": self.tasks["email-01-reschedule"]})
        failures = run_jobs(jobs, {"claude": FakeProvider(fail_on=[1])}, self.run_dir)
        self.assertEqual(len(failures), 1)
        self.assertFalse((self.run_dir / "drafts" / "email-01-reschedule.txt").exists())
        self.assertEqual(count_calls(jobs, self.run_dir), 2)
        provider = FakeProvider()
        self.assertEqual(run_jobs(jobs, {"claude": provider}, self.run_dir), [])
        self.assertEqual(provider.calls, 2)
        self.assertTrue((self.run_dir / "drafts" / "email-01-reschedule.txt").exists())

    def test_fatal_error_stops_run(self):
        class Fatal:
            def generate(self, request):
                raise FatalGenerationError("bad key")

        with self.assertRaises(FatalGenerationError):
            run_jobs(plan_jobs([PLAIN], self.tasks), {"claude": Fatal()}, self.run_dir)

    def test_manifest_records_each_call(self):
        run_jobs(plan_jobs([PLAIN], self.tasks), {"claude": FakeProvider()}, self.run_dir)
        lines = (self.run_dir / MANIFEST_NAME).read_text().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertFalse(json.loads(lines[0])["fell_back"])

    def test_select_prefers_gate_then_fewer_tells(self):
        task = self.tasks["email-01-reschedule"]
        fails = "Sounds good."
        stock = ("Thursday won't work because of an exam. Friday after 1pm or Monday "
                 "morning works. Please don't hesitate to reach out.")
        clean = "Thursday won't work because of an exam. Friday after 1pm or Monday morning works."
        self.assertEqual(select_draft(task, [fails, stock, clean]), clean)

    def test_dry_run_sends_nothing(self):
        code = main(["--tasks", str(TASKS_DIR), "generate",
                     str(ROOT / "experiments" / "first.json"), "--run", str(self.run_dir),
                     "--human", str(Path(self.folder.name, "missing")),
                     "--only", "opus-default"])
        self.assertEqual(code, 0)
        self.assertFalse(self.run_dir.exists())

    def test_few_shot_without_examples_fails_clearly(self):
        code = main(["--tasks", str(TASKS_DIR), "generate",
                     str(ROOT / "experiments" / "first.json"), "--run", str(self.run_dir),
                     "--human", str(Path(self.folder.name, "missing"))])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
