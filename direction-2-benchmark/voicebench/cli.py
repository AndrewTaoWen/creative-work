"""Command line entry point."""

import argparse
from pathlib import Path

from voicebench.tasks import load_tasks


def _validate(args) -> int:
    tasks = load_tasks(args.tasks)
    kinds = sorted({task.kind for task in tasks.values()})
    for kind in kinds:
        count = sum(task.kind == kind for task in tasks.values())
        print(f"{kind}: {count} tasks")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voicebench")
    parser.add_argument("--tasks", type=Path, default=Path("tasks"))
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("validate", help="check the task files").set_defaults(run_command=_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.run_command(args)
    except (ValueError, OSError) as error:
        print(f"error: {error}")
        return 1
