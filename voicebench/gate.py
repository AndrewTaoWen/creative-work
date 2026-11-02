"""Pass/fail checks: a text that fails here can't win on style."""

from dataclasses import dataclass

from voicebench.tasks import Task
from voicebench.text import word_count


@dataclass(frozen=True)
class GateResult:
    words: int
    missing_facts: tuple[str, ...]
    forbidden_hits: tuple[str, ...]
    over_limit: bool

    @property
    def passed(self) -> bool:
        return not (self.missing_facts or self.forbidden_hits or self.over_limit)


def check_gate(task: Task, text: str) -> GateResult:
    count = word_count(text)
    # Patterns match across curly apostrophes the same way as straight ones.
    normalized = text.replace("’", "'")
    return GateResult(
        words=count,
        missing_facts=tuple(c.id for c in task.required_facts if not c.matches(normalized)),
        forbidden_hits=tuple(c.id for c in task.forbidden if c.matches(normalized)),
        over_limit=count > task.max_words,
    )
