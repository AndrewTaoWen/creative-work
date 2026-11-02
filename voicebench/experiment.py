"""Load experiment conditions and reject settings the APIs won't accept."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

PROVIDERS = {"claude", "openai"}
PROMPTS = {"plain", "style_guide", "few_shot"}
_CONDITION_ID = re.compile(r"[a-z0-9][a-z0-9.\-]*")


@dataclass(frozen=True)
class Condition:
    id: str
    provider: str
    model: str
    effort: str
    prompt: str
    drafts: int = 1
    temperature: float | None = None


def _parse_condition(raw: dict) -> Condition:
    try:
        condition = Condition(**raw)
    except TypeError as error:
        raise ValueError(f"bad condition {raw.get('id', raw)!r}: {error}")
    name = condition.id
    if not _CONDITION_ID.fullmatch(name):
        raise ValueError(f"{name}: id can only use lowercase letters, digits, dots and dashes")
    if condition.provider not in PROVIDERS:
        raise ValueError(f"{name}: unknown provider {condition.provider!r}")
    if condition.prompt not in PROMPTS:
        raise ValueError(f"{name}: unknown prompt {condition.prompt!r}")
    if condition.drafts < 1:
        raise ValueError(f"{name}: drafts must be at least 1")
    if condition.temperature is not None:
        # Claude rejects sampling parameters, and OpenAI drops them when reasoning is on.
        if condition.provider != "openai" or condition.effort != "none":
            raise ValueError(f"{name}: temperature needs provider openai with effort none")
    return condition


def load_experiment(path: Path) -> list[Condition]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    conditions = [_parse_condition(entry) for entry in raw["conditions"]]
    ids = [condition.id for condition in conditions]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: condition ids must be unique")
    return conditions
