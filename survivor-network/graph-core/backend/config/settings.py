from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "graph-core"
    app_env: str = "local"
    database_url: str = "postgresql://survivor:survivor-pw@localhost:5432/survivor"

    # --- LLM configuration ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    llm_enabled: bool = True          # kill-switch: set False to disable all LLM calls
    llm_timeout: int = 30             # seconds per LLM request
    llm_max_retries: int = 2          # retry on transient failures
    llm_temperature: float = 0.2      # lower = more deterministic for classification

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
