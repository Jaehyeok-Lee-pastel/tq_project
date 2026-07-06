from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "app-api"
    app_env: str = "local"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Supabase service role is backend-only (bypasses RLS).
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # OpenAI is optional; strategy recommendations work without it.
    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-mini"
    ai_max_output_tokens: int = 900
    ai_request_timeout_seconds: float = 20.0

    # Market data proxy. Yahoo is free delayed data; API-key providers can replace it.
    market_data_provider: str = "yahoo"
    market_data_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @cached_property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
