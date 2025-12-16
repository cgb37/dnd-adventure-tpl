from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from llm_api.services.config import Settings


def build_agent(*, output_type, system_prompt: str) -> Agent:
    settings = Settings()

    provider = settings.llm_provider

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
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        model = OpenAIChatModel(
            settings.openai_model,
            provider=OpenAIProvider(api_key=settings.openai_api_key),
        )
        return Agent(model, output_type=output_type, system_prompt=system_prompt)

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        model = AnthropicModel(
            settings.anthropic_model,
            provider=AnthropicProvider(api_key=settings.anthropic_api_key),
        )
        return Agent(model, output_type=output_type, system_prompt=system_prompt)

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        model = GoogleModel(
            settings.gemini_model,
            provider=GoogleProvider(api_key=settings.gemini_api_key),
        )
        return Agent(model, output_type=output_type, system_prompt=system_prompt)

    if provider == "mock":
        # Generators handle mock provider without PydanticAI.
        raise RuntimeError("mock provider must be handled by generator")

    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
