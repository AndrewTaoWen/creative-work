"""Model providers share one request and reply shape."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    model: str
    system: str
    user: str
    effort: str
    temperature: float | None = None


@dataclass(frozen=True)
class Reply:
    text: str
    input_tokens: int
    output_tokens: int
    served_by: str
    fell_back: bool = False


class GenerationError(Exception):
    """One request failed, and the run can carry on."""


class FatalGenerationError(Exception):
    """Every request would fail the same way, so the run should stop."""
