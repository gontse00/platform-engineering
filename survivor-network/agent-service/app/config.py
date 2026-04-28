from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "agent-service"
    environment: str = "dev"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    llm_enabled: bool = True
    llm_timeout: int = 30
    llm_max_retries: int = 2
    llm_temperature: float = 0.2

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
