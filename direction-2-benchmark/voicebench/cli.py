"""Command line entry point."""

import argparse
from pathlib import Path

from voicebench.panel import KEY_NAME, SHEET_NAME, build_packet
from voicebench.runs import load_run
from voicebench.scoring import load_baselines, score_output, summarize, write_scores
from voicebench.tasks import load_tasks


def _validate(args) -> int:
    tasks = load_tasks(args.tasks)
    kinds = sorted({task.kind for task in tasks.values()})
    for kind in kinds:
        count = sum(task.kind == kind for task in tasks.values())
        print(f"{kind}: {count} tasks")
    return 0


def _score(args) -> int:
    tasks = load_tasks(args.tasks)
    baselines = load_baselines(args.human)
    rows = [score_output(output, baselines) for output in load_run(args.run, tasks)]
    out = args.out or args.run / "scores.csv"
    write_scores(rows, out)
    for row in summarize(rows):
        distance = row["mean_style_distance"]
        print(
            f"{row['condition']}: {row['outputs']} outputs, "
            f"gate {row['gate_pass_rate']:.0%}, "
            f"tells {row['mean_tell_rate']:.2f}/100 words, "
            f"style distance {'n/a' if distance is None else f'{distance:.2f}'}"
        )
    print(f"wrote {out}")
    return 0


def _panel(args) -> int:
    tasks = load_tasks(args.tasks)
    outputs = load_run(args.run, tasks)
    count = build_packet(outputs, args.out, args.seed, args.include_failed)
    print(f"wrote {count} items to {args.out / SHEET_NAME}")
    print(f"keep {args.out / KEY_NAME} away from raters")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voicebench")
    parser.add_argument("--tasks", type=Path, default=Path("tasks"))
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("validate", help="check the task files").set_defaults(run_command=_validate)

    score = commands.add_parser("score", help="score a run")
    score.add_argument("run", type=Path)
    score.add_argument("--human", type=Path, help="folder of <kind>/*.txt human baselines")
    score.add_argument("--out", type=Path)
    score.set_defaults(run_command=_score)

    panel = commands.add_parser("panel", help="build a blind rating sheet")
    panel.add_argument("run", type=Path)
    panel.add_argument("--out", type=Path, required=True)
    panel.add_argument("--seed", type=int, help="only for reproducible tests")
    panel.add_argument("--include-failed", action="store_true")
    panel.set_defaults(run_command=_panel)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.run_command(args)
    except (ValueError, OSError) as error:
        print(f"error: {error}")
        return 1
