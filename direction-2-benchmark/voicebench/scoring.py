"""Score each output in a run."""

import csv
import statistics
from collections import defaultdict
from pathlib import Path

from voicebench.gate import check_gate
from voicebench.runs import Output
from voicebench.style import MIN_BASELINE_TEXTS, Baseline
from voicebench.tells import tell_rate

FIELDS = [
    "condition",
    "task_id",
    "kind",
    "split",
    "words",
    "gate_passed",
    "missing_facts",
    "forbidden_hits",
    "over_limit",
    "tell_rate",
    "style_distance",
]


def load_baselines(human_dir: Path | None) -> dict[str, Baseline]:
    """Load <human_dir>/<kind>/*.txt, skipping kinds with too few texts."""
    if human_dir is None:
        return {}
    baselines = {}
    for kind_dir in sorted(path for path in Path(human_dir).iterdir() if path.is_dir()):
        texts = [path.read_text(encoding="utf-8") for path in sorted(kind_dir.glob("*.txt"))]
        if len(texts) >= MIN_BASELINE_TEXTS:
            baselines[kind_dir.name] = Baseline(texts)
    return baselines


def score_output(output: Output, baselines: dict[str, Baseline]) -> dict:
    gate = check_gate(output.task, output.text)
    baseline = baselines.get(output.task.kind)
    return {
        "condition": output.condition,
        "task_id": output.task.id,
        "kind": output.task.kind,
        "split": output.task.split,
        "words": gate.words,
        "gate_passed": gate.passed,
        "missing_facts": ";".join(gate.missing_facts),
        "forbidden_hits": ";".join(gate.forbidden_hits),
        "over_limit": gate.over_limit,
        "tell_rate": round(tell_rate(output.text, output.task.kind), 3),
        "style_distance": round(baseline.distance(output.text), 3) if baseline else "",
    }


def write_scores(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["condition"]].append(row)
    summary = []
    for condition, group in sorted(grouped.items()):
        distances = [row["style_distance"] for row in group if row["style_distance"] != ""]
        summary.append(
            {
                "condition": condition,
                "outputs": len(group),
                "gate_pass_rate": sum(row["gate_passed"] for row in group) / len(group),
                "mean_tell_rate": statistics.fmean(row["tell_rate"] for row in group),
                "mean_style_distance": statistics.fmean(distances) if distances else None,
            }
        )
    return summary
