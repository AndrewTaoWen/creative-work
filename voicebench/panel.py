"""Build a blind rating sheet, with the answer key in a separate file."""

import csv
import random
from pathlib import Path

from voicebench.gate import check_gate
from voicebench.runs import Output

SHEET_NAME = "panel_sheet.csv"
KEY_NAME = "panel_key.csv"
SHEET_FIELDS = ["item", "situation", "text", "sounds_human_1_to_5", "would_send_1_to_5", "notes"]
KEY_FIELDS = ["item", "condition", "task_id"]


def build_packet(
    outputs: list[Output], out_dir: Path, seed: int | None = None, include_failed: bool = False
) -> int:
    # Without a seed, nobody can rebuild the shuffle from the sheet alone.
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    selected = [o for o in outputs if include_failed or check_gate(o.task, o.text).passed]
    if not selected:
        raise ValueError("no outputs passed the gate; nothing to rate")
    rng.shuffle(selected)
    item_ids = rng.sample(range(1000, 10000), len(selected))

    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / SHEET_NAME).open("w", newline="", encoding="utf-8") as sheet_file:
        sheet = csv.DictWriter(sheet_file, fieldnames=SHEET_FIELDS)
        sheet.writeheader()
        for item, output in zip(item_ids, selected):
            sheet.writerow({"item": item, "situation": output.task.title, "text": output.text})
    with (out_dir / KEY_NAME).open("w", newline="", encoding="utf-8") as key_file:
        key = csv.DictWriter(key_file, fieldnames=KEY_FIELDS)
        key.writeheader()
        rows = [
            {"item": item, "condition": output.condition, "task_id": output.task.id}
            for item, output in zip(item_ids, selected)
        ]
        key.writerows(sorted(rows, key=lambda row: row["item"]))
    return len(selected)
