# creative-work

A benchmark for short functional writing: does this sound like a person, and does it do the job correctly? The reasoning is in the [research report](reports/Fixing%20AI%20sounding%20LLM%20writing.md).

The tools need Python 3.10 or later. Scoring has no other dependencies. Generating text needs the SDKs:

```bash
pip install -r requirements.txt
```

## Layout

- `tasks/`: benchmark tasks. There are 5 email tasks and 5 take-home tasks so far.
- `experiments/`: the conditions to compare.
- `voicebench/`: the generation and scoring tools.
- `tests/`: unit tests and fixtures.

## Usage

Check the task files:

```bash
python3 -m voicebench validate
```

See how many API calls an experiment needs. This sends nothing:

```bash
python3 -m voicebench generate experiments/first.json --run runs/first
```

The `opus-few-shot` condition needs 5 human texts in each of `data/human/email/examples/` and `data/human/takehome/examples/`. To leave it out, list the other conditions with `--only`.

Add `--execute` to make the calls. This costs money and needs `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`:

```bash
python3 -m voicebench generate experiments/first.json --run runs/first --execute
```

Finished outputs are kept, so running the command again only fills the gaps. Each call is logged in `runs/<run>/manifest.jsonl`. If a Claude request is declined and a fallback model answers, `fell_back` is true, and that output should be excluded from the comparison.

Generated outputs land in `runs/<run>/<condition>/<task_id>.txt`. Score a run with the command below. `--human` is optional:

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

The `opus-best-of-8` condition picks its final text with the gate and tell rate. Because the tell list isn't calibrated, treat that condition as a test of this selection rule, not of selection in general.

Only put genuinely human text in `data/human/`. `data/human/`, `runs/` and `panel/` are ignored by git.
