"""Compare surface style against a human baseline.

These features are a quick stand-in for a Biber analysis, which needs a
part-of-speech tagger. Only genuinely human text belongs in the baseline.
"""

import re
import statistics

from voicebench.text import sentences, words

MIN_BASELINE_TEXTS = 5
_MIN_SPREAD = 1e-6

_CONTRACTION = re.compile(r"\b\w+['’](?:s|t|re|ve|ll|d|m)\b", re.IGNORECASE)
_FIRST_PERSON = re.compile(r"\b(?:i|i['’]\w+|me|my|mine|we|our|us)\b", re.IGNORECASE)
_NOMINAL = re.compile(r"\b\w{3,}(?:tion|tions|ment|ments|ness|ity|ities)\b", re.IGNORECASE)
_LIST_LINE = re.compile(r"^\s*(?:[-*]|\d+\.) ", re.MULTILINE)


def features(text: str) -> dict[str, float]:
    tokens = words(text)
    lengths = [len(words(sentence)) for sentence in sentences(text)]
    lines = [line for line in text.splitlines() if line.strip()]
    per_1k = 1000 / max(len(tokens), 1)
    return {
        "sentence_mean": statistics.fmean(lengths) if lengths else 0.0,
        "sentence_spread": statistics.pstdev(lengths) if lengths else 0.0,
        "word_length": statistics.fmean(len(t) for t in tokens) if tokens else 0.0,
        "contractions": len(_CONTRACTION.findall(text)) * per_1k,
        "first_person": len(_FIRST_PERSON.findall(text)) * per_1k,
        "nominals": len(_NOMINAL.findall(text)) * per_1k,
        "em_dashes": text.count("—") * per_1k,
        "list_share": len(_LIST_LINE.findall(text)) / max(len(lines), 1),
    }


class Baseline:
    def __init__(self, texts: list[str]):
        if len(texts) < MIN_BASELINE_TEXTS:
            raise ValueError(
                f"baseline needs at least {MIN_BASELINE_TEXTS} texts, got {len(texts)}"
            )
        rows = [features(text) for text in texts]
        self.means = {name: statistics.fmean(row[name] for row in rows) for name in rows[0]}
        self.spreads = {
            name: max(statistics.pstdev(row[name] for row in rows), _MIN_SPREAD)
            for name in rows[0]
        }

    def distance(self, text: str) -> float:
        """Return the mean absolute z-score across features."""
        row = features(text)
        return statistics.fmean(
            abs(row[name] - self.means[name]) / self.spreads[name] for name in row
        )
