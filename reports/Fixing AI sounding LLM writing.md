# Fixing AI sounding LLM writing

Research date: 2026-10-31

## Recommendation

Build a narrow version of Direction 2, and use the judge idea from Direction 1 as its scorer. Don't make temperature the main lever.

- **Scope:** a benchmark for short functional writing, starting with email replies and take-home write-ups. I found no benchmark aimed squarely at this.
- **Why not temperature:** it is unavailable on many frontier models, and the studies found here show weak effects on style.
- **What to test instead:** few-shot examples of the writer's own text, retrieval of their past writing, and fine-tuning. These have the strongest evidence.

## Is the regression real?

Partly. There is one clear provider admission, but I found no controlled measurement across model generations.

- **Admission:** Sam Altman said OpenAI "screwed up" GPT-5.2's writing, according to [TechRadar](https://www.techradar.com/ai-platforms-assistants/sam-altman-admits-openai-screwed-up-the-writing-quality-on-chatgpt-5-2-and-promises-future-versions-wont-neglect-it). [Search Engine Journal](https://www.searchenginejournal.com/sam-altman-says-openai-screwed-up-gpt-5-2-writing-quality/565925/) reports he attributed this to prioritising coding and reasoning. I didn't find the primary transcript.
- **Scope of that evidence:** it covers one model. It doesn't show that all frontier models got worse.
- **Better-supported cause:** instruction tuning itself. A [PNAS study](https://arxiv.org/abs/2410.16107) found that differences from human writing are larger for instruction-tuned models than for base models. A [2026 study](https://arxiv.org/abs/2604.14111) found chat variants cluster together in style.
- **Possible contributors, less certain:** a [2026 paper](https://preview.aclanthology.org/ingest-eacl/2026.latechclfl-1.13.pdf) argues annotators imprint their style during post-training. Preference votes may also reward the wrong things: secondary explainers report that length was the largest style effect in [LMArena's own analysis](https://bestllmfor.com/guides/lmarena-leaderboard-explained/). Linking that to a writing regression is my inference.

So the problem may be less a sudden decline than a persistent house style that readers now recognise easily, with some models also getting worse. This is my reading, and it can be tested.

## What makes text read as AI

- **Catalogued patterns:** [Wikipedia's guide](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) lists negative parallelisms, overused words such as "moreover", emojis in headers and knowledge-cutoff disclaimers. It is qualitative and specific to Wikipedia, and I found no precision or recall figures for it.
- **Deeper style shifts:** [a study of 16 frontier models](https://arxiv.org/abs/2509.10179v2) treats LLM quirks as movement along underlying style dimensions, not isolated word habits. Word lists also go stale, so grammar and register measures are likely to last longer (my inference).
- **Who can tell:** in [Russell et al. (ACL 2025)](https://arxiv.org/abs/2501.15654), people who don't use LLMs for writing performed near chance. Five experienced users reached a 92.7% true positive rate and a 3.3% false positive rate. That is a small group, but it shows who should be on your panel.

## Direction 1: temperature plus a judge

### Temperature is often not available

| Provider | Current rule |
|---|---|
| OpenAI | [Remove `temperature` and `top_p`](https://developers.openai.com/api/docs/guides/latest-model) whenever reasoning effort isn't `none`. GPT-6 Astra and GPT-6.1 Sol don't accept `none`. GPT-6.1 Terra, GPT-6 Sol and GPT-6 Luna do. |
| Anthropic | [Claude Opus 5.5 rejects sampling parameters](https://platform.claude.com/docs/en/models/opus-5-5/migration-guide) with a 400 error and recommends prompting instead. On [API version 2026-10-21](https://platform.claude.com/docs/en/api/migration-2026-10-21), sending them returns a 400 on every model, even at default values. |

Open-weight models keep full sampler control. I didn't check Gemini, xAI, DeepSeek or Mistral.

### Temperature has weak effects on style

- **Stories:** a [2024 study](https://arxiv.org/abs/2405.00492) found higher temperature weakly tied to novelty and moderately tied to incoherence, with no link to typicality.
- **Style:** the [2026 Biber-feature study](https://arxiv.org/abs/2604.14111) found model and genre matter more than decoding strategy or prompting, with some exceptions. Differences from human text persisted even under prompts meant to sound more human.
- **Iterative generation:** a [2026 pilot on recipes](https://arxiv.org/abs/2608.07243) found temperature had limited effects except on originality, while evaluator design was the strongest lever. Recipes aren't prose, so this is only suggestive.
- **Min-p:** don't rely on it. A [published critique](https://arxiv.org/abs/2506.13681) says the original evidence doesn't support its quality and diversity claims.

I found no study that isolates temperature's effect on prose style across many models, so a small test is still worthwhile.

### The judge is the useful part

Selecting from several drafts can work without temperature, because drafts can vary by model, prompt or random seed. Choosing the judge is the hard part:

| Judge | Strength | Limit |
|---|---|---|
| Commercial detector | [Epoch AI's July 2026 test](https://epoch.ai/data-insights/ai-detectors-false-negatives): Pangram and GPTZero flagged 0 of 495 human passages and caught nearly all basic-prompt AI text. [An NBER paper](https://www.nber.org/system/files/working_papers/w34223/w34223.pdf) also favours Pangram. | It measures origin, not quality. [Many detectors fail on humanized text](https://aclanthology.org/people/max-spero), according to authors who include Pangram's founders. |
| Off-the-shelf LLM judge | Cheap and easy to run. | The best in [LitBench](https://aclanthology.org/2026.eacl-long.362) agreed with human preferences 73% of the time, on fiction. |
| Trained reward model | Reached 78% in LitBench, on fiction. | Needs a lot of labelled pairs (LitBench trained on 43,827). |
| Experienced human panel | The best available ground truth. | Slow, and the evidence comes from five people. |

## Direction 2: a scoring system

- **[LitBench](https://aclanthology.org/2026.eacl-long.362)** has the strongest labels I found, but covers Reddit stories only. Its authors argue that EQ-Bench and WritingBench assume zero-shot LLM judges are reliable.
- **[WritingBench](https://arxiv.org/abs/2503.05244)** spans 1,239 queries across 6 domains, including technical writing, but isn't built around human-likeness.
- **Email:** a [2025 review](https://www.mdpi.com/1999-5903/17/12/536) finds gaps in benchmarks and user-centred evaluation for LLM email systems. [Panza](https://arxiv.org/abs/2407.10994), the main email-specific system I found, uses metrics rather than human raters.

The opening is a benchmark that measures two things separately: does this sound like a person, and does it do the job correctly?

## What actually changes style

- **Few-shot examples:** a cheap and measurable first step. In Epoch's test, five reference passages raised detector misses from under 1% to 10–18%. A separate [EMNLP 2025 study](https://arxiv.org/abs/2509.14543) found models imitate email style better than blog or forum style, but still calls personal style imitation a fundamental gap.
- **Fine-tuning:** the strongest result found. In [Chakrabarty et al.](https://arxiv.org/abs/2510.13939), detectors flagged about 3% of fine-tuned excerpts versus 97% of prompted ones, and both reader groups preferred the fine-tuned AI text. This used complete works by award-winning authors at a median cost of $81 per author, so it may not carry over to someone's emails.
- **Retrieval plus fine-tuning:** Panza combines both for email and is worth copying as a design, though its human-likeness is unproven.

## First experiment

These numbers and thresholds are my proposals, not research findings.

1. **Tasks:** write 30 tasks: 15 email replies with thread context and 15 take-home write-ups from a real repo. Each task lists the facts the text must include.
2. **Human baseline:** collect comparable human text. Your own emails work, as do pre-2022 READMEs and the public Enron email corpus.
3. **Conditions:**
   - default output
   - style guide with banned patterns
   - five samples of the writer's text
   - eight drafts, then select the best
   - fine-tuned model, if a suitable base model is available
   - temperature sweep at 0.7, 1.0 and 1.3 on GPT-6.1 Terra with effort `none`, plus one open-weight model
4. **Scores:**
   - Pass or fail on required facts, using a checklist. A text that fails can't win.
   - Humanness from a blind panel of 3–5 people who regularly write with LLMs.
   - Cheap signals: detector score, Biber-feature distance from the human baseline, and tell rate.
5. **Calibration:** check which cheap signals predict panel judgments on held-out tasks. Keep only those that do.
6. **Decision:** drop temperature if the sweep moves panel scores less than the gap between default output and five-shot examples.

Keep a hidden set of tasks and report humanness and accuracy separately, so that no one can tune to a single number. Optimising directly against a detector or fixed judge will probably just create new tells.

If this is used for job applications, check each take-home's AI policy. Aim for the writer's own voice, not detector evasion.

## Limits of this research

- I did this research directly because the research agents couldn't start.
- I read abstract pages, not full papers, for most studies. The Altman, min-p, Peeperkorn, WritingBench, NBER, humanizer and LMArena items come from search summaries or secondary coverage.
- Earlier versions of Chakrabarty et al. report different sample sizes, so I cited the March 2026 version and left out its odds ratios.
- Most reader and judge evidence comes from fiction or longer non-fiction. None of it directly tests whether a short email reply sounds human.
