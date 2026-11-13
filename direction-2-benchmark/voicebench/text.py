"""Small text helpers shared by the scorers."""

import re

_WORD = re.compile(r"[A-Za-z0-9]+(?:['’.\-_/:][A-Za-z0-9]+)*")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def words(text: str) -> list[str]:
    return _WORD.findall(text)


def word_count(text: str) -> int:
    return len(words(text))


def sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_END.split(text) if words(part)]
