"""Read a run laid out as <run>/<condition>/<task_id>.txt."""

from dataclasses import dataclass
from pathlib import Path

from voicebench.tasks import Task


@dataclass(frozen=True)
class Output:
    condition: str
    task: Task
    text: str


def load_run(run_dir: Path, tasks: dict[str, Task]) -> list[Output]:
    conditions = sorted(path for path in Path(run_dir).iterdir() if path.is_dir())
    outputs = []
    for condition in conditions:
        for path in sorted(condition.glob("*.txt")):
            if path.stem not in tasks:
                raise ValueError(f"{path}: no task named {path.stem!r}")
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                raise ValueError(f"{path}: file is empty")
            outputs.append(Output(condition.name, tasks[path.stem], text))
    if not outputs:
        raise ValueError(f"no outputs found in {run_dir}")
    return outputs
