"""Load benchmark tasks and reject malformed ones."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

KINDS = {"email", "takehome"}
REQUIRED_FIELDS = {
    "id": str,
    "kind": str,
    "title": str,
    "persona": str,
    "context": str,
    "instruction": str,
    "max_words": int,
    "required_facts": list,
    "forbidden": list,
}


@dataclass(frozen=True)
class Check:
    id: str
    description: str
    patterns: tuple[re.Pattern, ...]

    def matches(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in self.patterns)


@dataclass(frozen=True)
class Task:
    id: str
    kind: str
    title: str
    persona: str
    context: str
    instruction: str
    max_words: int
    required_facts: tuple[Check, ...]
    forbidden: tuple[Check, ...]

    @property
    def prompt(self) -> str:
        return f"{self.persona}\n\n{self.context}\n\n{self.instruction}"


def _parse_check(raw: dict, task_id: str) -> Check:
    for field in ("id", "description", "any_of"):
        if field not in raw:
            raise ValueError(f"{task_id}: check is missing {field!r}")
    if not raw["any_of"]:
        raise ValueError(f"{task_id}: check {raw['id']!r} has no patterns")
    try:
        patterns = tuple(re.compile(p, re.IGNORECASE) for p in raw["any_of"])
    except re.error as error:
        raise ValueError(f"{task_id}: check {raw['id']!r} has a bad pattern: {error}")
    return Check(raw["id"], raw["description"], patterns)


def _parse_task(raw: dict) -> Task:
    task_id = raw.get("id", "<no id>")
    for field, expected in REQUIRED_FIELDS.items():
        if not isinstance(raw.get(field), expected):
            raise ValueError(f"{task_id}: {field!r} must be {expected.__name__}")
    if raw["kind"] not in KINDS:
        raise ValueError(f"{task_id}: unknown kind {raw['kind']!r}")
    if raw["max_words"] <= 0:
        raise ValueError(f"{task_id}: max_words must be positive")
    if not raw["required_facts"]:
        raise ValueError(f"{task_id}: needs at least one required fact")
    checks = raw["required_facts"] + raw["forbidden"]
    check_ids = [check.get("id") for check in checks]
    if len(check_ids) != len(set(check_ids)):
        raise ValueError(f"{task_id}: check ids must be unique")
    return Task(
        id=raw["id"],
        kind=raw["kind"],
        title=raw["title"],
        persona=raw["persona"],
        context=raw["context"],
        instruction=raw["instruction"],
        max_words=raw["max_words"],
        required_facts=tuple(_parse_check(c, task_id) for c in raw["required_facts"]),
        forbidden=tuple(_parse_check(c, task_id) for c in raw["forbidden"]),
    )


def load_tasks(directory: Path) -> dict[str, Task]:
    tasks: dict[str, Task] = {}
    paths = sorted(Path(directory).glob("*.json"))
    if not paths:
        raise ValueError(f"no task files in {directory}")
    for path in paths:
        for raw in json.loads(path.read_text(encoding="utf-8")):
            task = _parse_task(raw)
            if task.id in tasks:
                raise ValueError(f"duplicate task id {task.id!r} in {path}")
            tasks[task.id] = task
    return tasks
