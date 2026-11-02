"""Generate outputs for an experiment. Finished work is kept, so a rerun resumes."""

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from voicebench.experiment import Condition
from voicebench.gate import check_gate
from voicebench.prompts import build_system, load_examples
from voicebench.providers import GenerationError, Reply, Request
from voicebench.tasks import Task
from voicebench.tells import tell_rate

MANIFEST_NAME = "manifest.jsonl"


class Provider(Protocol):
    def generate(self, request: Request) -> Reply: ...


@dataclass(frozen=True)
class Job:
    condition: Condition
    task: Task
    system: str

    @property
    def request(self) -> Request:
        return Request(
            model=self.condition.model,
            system=self.system,
            user=self.task.prompt,
            effort=self.condition.effort,
            temperature=self.condition.temperature,
        )


def plan_jobs(
    conditions: list[Condition], tasks: dict[str, Task], human_dir: Path | None = None
) -> list[Job]:
    jobs = []
    for condition in conditions:
        for task in tasks.values():
            examples = None
            if condition.prompt == "few_shot":
                examples = load_examples(human_dir, task.kind)
            jobs.append(Job(condition, task, build_system(condition.prompt, examples)))
    return jobs


def select_draft(task: Task, drafts: list[str]) -> str:
    """Prefer drafts that pass the gate, then the lowest tell rate, then the earliest."""
    return min(drafts, key=lambda d: (not check_gate(task, d).passed, tell_rate(d, task.kind)))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".partial")
    partial.write_text(text + "\n", encoding="utf-8")
    os.replace(partial, path)


def _log(run_dir: Path, job: Job, draft: int, reply: Reply) -> None:
    entry = {
        "condition": job.condition.id,
        "task_id": job.task.id,
        "draft": draft,
        "requested_model": job.condition.model,
        "served_by": reply.served_by,
        "fell_back": reply.fell_back,
        "effort": job.condition.effort,
        "temperature": job.condition.temperature,
        "system_sha256": hashlib.sha256(job.system.encode()).hexdigest(),
        "user_sha256": hashlib.sha256(job.task.prompt.encode()).hexdigest(),
        "input_tokens": reply.input_tokens,
        "output_tokens": reply.output_tokens,
    }
    with (run_dir / MANIFEST_NAME).open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry) + "\n")


def count_calls(jobs: list[Job], run_dir: Path) -> int:
    """Count the requests still needed, which is what a run would cost."""
    return sum(len(_missing_drafts(job, run_dir)) for job in jobs)


def _output_path(job: Job, run_dir: Path) -> Path:
    return run_dir / job.condition.id / f"{job.task.id}.txt"


def _draft_path(job: Job, run_dir: Path, draft: int) -> Path:
    return run_dir / job.condition.id / "drafts" / f"{job.task.id}.{draft}.txt"


def _missing_drafts(job: Job, run_dir: Path) -> list[int]:
    if _output_path(job, run_dir).exists():
        return []
    if job.condition.drafts == 1:
        return [0]
    return [
        draft
        for draft in range(job.condition.drafts)
        if not _draft_path(job, run_dir, draft).exists()
    ]


def run_job(job: Job, provider: Provider, run_dir: Path) -> None:
    """Generate a job's text. A multi-draft job selects only once every draft exists."""
    if job.condition.drafts == 1:
        if _missing_drafts(job, run_dir):
            reply = provider.generate(job.request)
            _write(_output_path(job, run_dir), reply.text)
            _log(run_dir, job, 0, reply)
        return

    for draft in _missing_drafts(job, run_dir):
        reply = provider.generate(job.request)
        _write(_draft_path(job, run_dir, draft), reply.text)
        _log(run_dir, job, draft, reply)
    if not _output_path(job, run_dir).exists():
        paths = [_draft_path(job, run_dir, d) for d in range(job.condition.drafts)]
        drafts = [path.read_text(encoding="utf-8").strip() for path in paths]
        _write(_output_path(job, run_dir), select_draft(job.task, drafts))


def run_jobs(
    jobs: list[Job], providers: dict[str, Provider], run_dir: Path
) -> list[tuple[Job, str]]:
    """Run every job and return the failures. A fatal error stops the run."""
    run_dir.mkdir(parents=True, exist_ok=True)
    failures = []
    for job in jobs:
        try:
            run_job(job, providers[job.condition.provider], run_dir)
        except GenerationError as error:
            failures.append((job, str(error)))
    return failures
