# creative-work

A benchmark for short functional writing: does this sound like a person, and does it do the job correctly? The reasoning is in the [research report](reports/Fixing%20AI%20sounding%20LLM%20writing.md).

The tools need Python 3.10 or later and have no other dependencies.

## Layout

- `tasks/`: benchmark tasks. There are 5 email tasks and 5 take-home tasks so far.
- `voicebench/`: the scoring tools.
- `tests/`: unit tests and fixtures.

## Usage

Check the task files:

```bash
python3 -m voicebench validate
```

Put each model output in `runs/<run>/<condition>/<task_id>.txt`, then score the run. `--human` is optional:

```bash
python3 -m voicebench score runs/demo --human data/human
```

Build a blind sheet for raters. Keep `panel_key.csv` away from them:

```bash
python3 -m voicebench panel runs/demo --out panel/demo
```

Run the tests:

```bash
python3 -m unittest discover -s tests
```

## Scores

- **Gate:** pass or fail. A text fails if it misses a required fact, makes a forbidden claim or goes over the word limit. Facts are checked with regular expressions, so review failures by hand, because an unusual but correct phrasing can fail.
- **Tell rate:** phrases associated with AI prose, per 100 words. The lists aren't calibrated yet.
- **Style distance:** how far surface style sits from human text, as a mean z-score. This is a simplified stand-in for a Biber analysis. It needs at least 5 texts in `data/human/<kind>/`.
- **Panel ratings:** the ground truth. Other signals only count if they predict these.

Only put genuinely human text in `data/human/`. `data/human/`, `runs/` and `panel/` are ignored by git.
