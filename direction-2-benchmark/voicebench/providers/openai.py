"""Call OpenAI models through the Responses API."""

import openai

from voicebench.providers import FatalGenerationError, GenerationError, Reply, Request

MAX_OUTPUT_TOKENS = 16000


class OpenAIProvider:
    def __init__(self, client: openai.OpenAI | None = None):
        self.client = client or openai.OpenAI()

    def generate(self, request: Request) -> Reply:
        options = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        try:
            response = self.client.responses.create(
                model=request.model,
                instructions=request.system,
                input=request.user,
                reasoning={"effort": request.effort},
                max_output_tokens=MAX_OUTPUT_TOKENS,
                **options,
            )
        except (
            openai.AuthenticationError,
            openai.PermissionDeniedError,
            openai.NotFoundError,
            openai.BadRequestError,
        ) as error:
            raise FatalGenerationError(str(error)) from error
        except openai.RateLimitError as error:
            raise GenerationError(f"rate limited: {error}") from error
        except openai.APIStatusError as error:
            raise GenerationError(f"API error {error.status_code}: {error}") from error
        except openai.APIConnectionError as error:
            raise GenerationError(f"connection failed: {error}") from error

        if response.status != "completed":
            raise GenerationError(f"stopped early: {response.status}")
        text = response.output_text.strip()
        if not text:
            raise GenerationError("reply had no text")
        return Reply(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            served_by=response.model,
        )
