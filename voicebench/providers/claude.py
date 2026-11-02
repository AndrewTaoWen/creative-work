"""Call Claude through the Anthropic SDK."""

import anthropic

from voicebench.providers import FatalGenerationError, GenerationError, Reply, Request

MAX_TOKENS = 16000
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ClaudeProvider:
    def __init__(self, client: anthropic.Anthropic | None = None):
        self.client = client or anthropic.Anthropic()

    def generate(self, request: Request) -> Reply:
        try:
            response = self.client.beta.messages.create(
                model=request.model,
                max_tokens=MAX_TOKENS,
                system=request.system,
                messages=[{"role": "user", "content": request.user}],
                thinking={"type": "adaptive"},
                output_config={"effort": request.effort},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except (
            anthropic.AuthenticationError,
            anthropic.PermissionDeniedError,
            anthropic.NotFoundError,
            anthropic.BadRequestError,
        ) as error:
            raise FatalGenerationError(str(error)) from error
        except anthropic.RateLimitError as error:
            raise GenerationError(f"rate limited: {error}") from error
        except anthropic.APIStatusError as error:
            raise GenerationError(f"API error {error.status_code}: {error}") from error
        except anthropic.APIConnectionError as error:
            raise GenerationError(f"connection failed: {error}") from error

        if response.stop_reason != "end_turn":
            raise GenerationError(f"stopped early: {response.stop_reason}")
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        if not text:
            raise GenerationError("reply had no text")
        iterations = response.usage.iterations or []
        return Reply(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            served_by=response.model,
            # A fallback means another model wrote this, so the manifest has to say so.
            fell_back=any(entry.type == "fallback_message" for entry in iterations),
        )
