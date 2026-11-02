# creative-work

Work on why LLM writing sounds AI generated, and what to do about it. The reasoning is in the [research report](reports/Fixing%20AI%20sounding%20LLM%20writing.md).

## Routes

- [`direction-1-temperature-judge/`](direction-1-temperature-judge/README.md): vary temperature, generate several drafts and use a judge to balance humanness and reasonability.
- [`direction-2-benchmark/`](direction-2-benchmark/README.md): an opinionated benchmark for short functional writing, with its tasks, scoring tools and test suite.

Direction 1 reuses the `voicebench` tools in Direction 2, so its commands run from `direction-2-benchmark/`. Direction 2 doesn't depend on Direction 1.

Both routes write to the same run folder, because the first experiment compares them on one blind panel sheet.
