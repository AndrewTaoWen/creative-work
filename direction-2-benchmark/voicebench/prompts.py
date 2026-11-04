"""Build the system prompt for each condition."""

from pathlib import Path

FEW_SHOT_EXAMPLES = 5

BASE = "Write only the requested text, ready to send. Add no preamble, notes or surrounding quotes."

STYLE_GUIDE = """Write the way a busy, competent person writes to someone they work with.
Use plain words and contractions. Put the point first and stop when you've made it.
Vary sentence length, and let some sentences be short or a little informal.
Don't open with pleasantries about the reader or close with offers of more help.
Don't use contrast pairs such as "not X but Y", groups of three for rhythm, or em dashes.
Don't use headers, bold text or bullets in an email.
Be specific, and don't claim more than the facts support."""


def load_examples(human_dir: Path | None, kind: str) -> list[str]:
    """Load examples kept apart from the baseline, so they can't flatter style distance."""
    folder = Path(human_dir or "data/human") / kind / "examples"
    paths = sorted(folder.glob("*.txt"))[:FEW_SHOT_EXAMPLES]
    if len(paths) < FEW_SHOT_EXAMPLES:
        raise ValueError(
            f"few_shot needs {FEW_SHOT_EXAMPLES} human texts in {folder}, found {len(paths)}"
        )
    return [path.read_text(encoding="utf-8").strip() for path in paths]


def build_system(prompt: str, examples: list[str] | None = None) -> str:
    if prompt == "plain":
        return BASE
    if prompt == "style_guide":
        return f"{BASE}\n\n{STYLE_GUIDE}"
    if prompt == "few_shot":
        blocks = "\n".join(f"<example>\n{text}\n</example>" for text in examples or [])
        return f"{BASE}\n\nMatch the voice of this writer's own examples:\n{blocks}"
    raise ValueError(f"unknown prompt {prompt!r}")
