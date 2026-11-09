# Direction 1: temperature plus a judge

Does temperature change how human the writing sounds, and can a judge pick the best draft? The [research report](../reports/Fixing%20AI%20sounding%20LLM%20writing.md) expects temperature to matter little, so this is a small test. Selecting between drafts is the more promising half.

## Conditions

[`experiments/first.json`](experiments/first.json) holds 4 conditions:

- `terra-temp-0.7`, `terra-temp-1.0` and `terra-temp-1.3`: a temperature sweep on GPT-6.1 Terra with reasoning effort `none`. The docs imply Terra accepts temperature at that effort, but no live call has confirmed it.
- `opus-best-of-8`: eight Claude Opus 5.5 drafts for each task, then one is selected.

## Usage

These commands use the tools in [Direction 2](../direction-2-benchmark/README.md), so run them from `direction-2-benchmark/`. See how many API calls are needed. This sends nothing:

```bash
python3 -m voicebench generate ../direction-1-temperature-judge/experiments/first.json --run runs/first
```

Add `--execute` to make the calls. This costs money and needs `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`:

```bash
python3 -m voicebench generate ../direction-1-temperature-judge/experiments/first.json --run runs/first --execute
```

Use the same `--run` folder as Direction 2. The decision rule compares the sweep with the gap between `opus-default` and `opus-few-shot`, and those two conditions come from Direction 2.

While you're still adjusting the judge, add `--split dev` before `generate`, and keep the held-out tasks for the final comparison. Direction 2 explains the [split](../direction-2-benchmark/README.md#dev-and-held-out-tasks).

## The judge

The only judge so far is `select_draft` in `voicebench/generate.py`. It picks a draft that passes the gate, then takes the lowest tell rate. Because the tell list isn't calibrated, treat `opus-best-of-8` as a test of this selection rule, not of selection in general.

## Not built

- A real judge, such as an LLM judge, a detector or a trained reward model. The report compares these options.
- An open-weight model for the sweep.
