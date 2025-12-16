from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from llm_api.services.config import Settings
from llm_api.services.errors import ApiError


def build_agent(*, output_type, system_prompt: str, provider_override: str | None = None) -> Agent:
    settings = Settings()  # pyright: ignore[reportCallIssue]

    provider = (provider_override or settings.llm_provider or "").strip().lower()

    if provider == "ollama":
        model = OpenAIChatModel(
            settings.ollama_model,
            provider=OpenAIProvider(
                base_url=f"{settings.ollama_base_url.rstrip('/')}/v1",
                api_key="ollama",  # not used by ollama, but required by client
            ),
        )
        return Agent(model, output_type=output_type, system_prompt=system_prompt)

    if provider == "openai":
        if not settings.openai_api_key:
            raise ApiError(
                code="provider_not_configured",
                message="OPENAI_API_KEY is required when provider=openai",
                status_code=400,
            )
        model = OpenAIChatModel(
            settings.openai_model,
            provider=OpenAIProvider(api_key=settings.openai_api_key),
        )
        return Agent(model, output_type=output_type, system_prompt=system_prompt)

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ApiError(
                code="provider_not_configured",
                message="ANTHROPIC_API_KEY is required when provider=anthropic",
                status_code=400,
            )
        model = AnthropicModel(
            settings.anthropic_model,
            provider=AnthropicProvider(api_key=settings.anthropic_api_key),
        )
        return Agent(model, output_type=output_type, system_prompt=system_prompt)

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise ApiError(
                code="provider_not_configured",
                message="GEMINI_API_KEY is required when provider=gemini",
                status_code=400,
            )
        model = GoogleModel(
            settings.gemini_model,
            provider=GoogleProvider(api_key=settings.gemini_api_key),
        )
        return Agent(model, output_type=output_type, system_prompt=system_prompt)

    if provider == "mock":
        # Generators handle mock provider without PydanticAI.
        raise RuntimeError("mock provider must be handled by generator")

    raise ApiError(
        code="unknown_provider",
        message=f"Unknown provider: {provider}",
        status_code=400,
    )
