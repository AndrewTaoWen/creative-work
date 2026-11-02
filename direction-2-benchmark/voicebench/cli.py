"""Command line entry point."""

import argparse
from pathlib import Path

from voicebench.experiment import load_experiment
from voicebench.generate import count_calls, plan_jobs, run_jobs
from voicebench.panel import KEY_NAME, SHEET_NAME, build_packet
from voicebench.providers import FatalGenerationError
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


def _build_providers(names: set[str]) -> dict:
    # Imported here so that scoring works without the SDKs installed.
    providers = {}
    if "claude" in names:
        from voicebench.providers.claude import ClaudeProvider

        providers["claude"] = ClaudeProvider()
    if "openai" in names:
        from voicebench.providers.openai import OpenAIProvider

        providers["openai"] = OpenAIProvider()
    return providers


def _generate(args) -> int:
    tasks = load_tasks(args.tasks)
    conditions = load_experiment(args.experiment)
    if args.only:
        conditions = [condition for condition in conditions if condition.id in args.only]
        unknown = set(args.only) - {condition.id for condition in conditions}
        if unknown:
            raise ValueError(f"unknown conditions: {', '.join(sorted(unknown))}")
    jobs = plan_jobs(conditions, tasks, args.human)
    calls = count_calls(jobs, args.run)
    print(f"{len(conditions)} conditions, {len(tasks)} tasks, {calls} API calls needed")
    if not args.execute:
        print("nothing was sent; add --execute to run these calls")
        return 0
    providers = _build_providers({condition.provider for condition in conditions})
    failures = run_jobs(jobs, providers, args.run)
    for job, reason in failures:
        print(f"failed {job.condition.id}/{job.task.id}: {reason}")
    print(f"done: {len(jobs) - len(failures)} of {len(jobs)} outputs finished")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voicebench")
    parser.add_argument("--tasks", type=Path, default=Path("tasks"))
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("validate", help="check the task files").set_defaults(run_command=_validate)

    generate = commands.add_parser("generate", help="plan or run model calls")
    generate.add_argument("experiment", type=Path)
    generate.add_argument("--run", type=Path, required=True)
    generate.add_argument("--human", type=Path, help="folder of <kind>/examples/*.txt")
    generate.add_argument("--only", nargs="+", help="condition ids to include")
    generate.add_argument("--execute", action="store_true", help="make the API calls")
    generate.set_defaults(run_command=_generate)

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
    except (ValueError, OSError, FatalGenerationError, ImportError) as error:
        print(f"error: {error}")
        return 1
