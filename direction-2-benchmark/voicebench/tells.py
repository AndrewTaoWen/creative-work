"""Count phrases associated with AI prose.

These lists are starting points drawn from the research report. They are not
calibrated, so treat the rate as a signal to test against panel ratings.
"""

import re

from voicebench.text import word_count


def _compile(*patterns: str) -> tuple[re.Pattern, ...]:
    return tuple(re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns)


TELLS = {
    "negative_parallelism": _compile(
        r"\bnot (?:just|only|merely)\b[^.!?\n]{0,80}\bbut\b",
        r"\b(?:it|this|that)(?:'s| is) not\b[^.!?\n]{1,60}[,;—–-]\s*(?:it|this|that)(?:'s| is)\b",
    ),
    "pet_words": _compile(
        r"\b(?:moreover|furthermore|additionally|delve|delves|delving|tapestry)\b",
        r"\b(?:seamless|seamlessly|leverage|leveraging|pivotal|meticulous|meticulously)\b",
    ),
    "stock_phrases": _compile(
        r"\bhope this (?:email|message|note) finds you\b",
        r"\bthank you for (?:reaching out|your patience|your understanding)\b",
        r"\b(?:don't|do not) hesitate to\b",
        r"\bfeel free to\b",
        r"\bplease let me know if you have any\b",
        r"\bi(?:'d| would) be happy to\b",
    ),
    "inflated_significance": _compile(
        r"\bplays? an? (?:vital|crucial|key|pivotal) role\b",
        r"\b(?:a|stands as a) testament to\b",
        r"\bhighlights? the importance\b",
        r"\bunderscores?\b",
    ),
    "assistant_voice": _compile(
        r"\bas an ai\b",
        r"\bas of my (?:last|latest)\b",
        r"\bcertainly!",
        r"\bhere(?:'s| is) (?:a|the|your) (?:draft|reply|response|email|readme)\b",
    ),
}

# Markdown is ordinary in a README, but it stands out in an email.
EMAIL_MARKUP = _compile(r"^#{1,6} ", r"\*\*[^*\n]+\*\*", r"^\s*[-*] ")


def tell_counts(text: str, kind: str) -> dict[str, int]:
    normalized = text.replace("’", "'")
    counts = {
        name: sum(len(pattern.findall(normalized)) for pattern in patterns)
        for name, patterns in TELLS.items()
    }
    if kind == "email":
        counts["email_markup"] = sum(len(p.findall(normalized)) for p in EMAIL_MARKUP)
    return counts


def tell_rate(text: str, kind: str) -> float:
    """Return tells per 100 words."""
    count = word_count(text)
    if count == 0:
        return 0.0
    return 100 * sum(tell_counts(text, kind).values()) / count
