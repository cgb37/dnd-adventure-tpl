from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_api_key: str = Field(alias="LLM_API_KEY")
    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")

    # Dev convenience: allow localhost callers (the Jekyll UI) without an API key.
    relax_auth_on_localhost: bool = Field(default=True, alias="RELAX_AUTH_ON_LOCALHOST")
    ui_origin: str = Field(default="http://localhost:4000", alias="UI_ORIGIN")

    # CORS allowlist. Keep this as a plain string so env vars can be set as
    # comma-separated values (e.g. "http://localhost:4000,http://127.0.0.1:4000").
    # Using list[str] here causes pydantic-settings to attempt JSON parsing.
    cors_allow_origins: str = Field(
        default="http://localhost:4000",
        alias="CORS_ALLOW_ORIGINS",
    )

    @property
    def cors_allow_origins_list(self) -> list[str]:
        raw = (self.cors_allow_origins or "").strip()
        if not raw:
            return ["http://localhost:4000"]
        items = [s.strip() for s in raw.split(",")]
        return [s for s in items if s]

    # Ollama (host-only; docker should use host.docker.internal)
    ollama_base_url: str = Field(default="http://host.docker.internal:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", alias="OLLAMA_MODEL")

    # Hosted providers
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-5-sonnet-latest", alias="ANTHROPIC_MODEL")

    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")

    # Limits
    max_concurrency: int = Field(default=4, alias="MAX_CONCURRENCY")
    max_concurrency_per_provider: int = Field(default=2, alias="MAX_CONCURRENCY_PER_PROVIDER")
    requests_per_minute: int = Field(default=30, alias="REQUESTS_PER_MINUTE")
    max_model_requests_per_generation: int = Field(
        default=3,
        alias="MAX_MODEL_REQUESTS_PER_GENERATION",
    )
    max_output_tokens: int = Field(default=1200, alias="MAX_OUTPUT_TOKENS")
    max_request_bytes: int = Field(default=200_000, alias="MAX_REQUEST_BYTES")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug_prompts: bool = Field(default=False, alias="DEBUG_PROMPTS")
