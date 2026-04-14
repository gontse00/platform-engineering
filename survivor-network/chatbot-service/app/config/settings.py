from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "chatbot-service"
    environment: str = "dev"

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/chatbot_service"
    graph_core_base_url: str = "http://graph-core:8080"

    attachment_storage_path: str = "/tmp/chatbot-attachments"

    # --- LLM configuration ---
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    llm_enabled: bool = True          # kill-switch: set False to disable all LLM calls
    llm_timeout: int = 30             # seconds per LLM request
    llm_max_retries: int = 2          # retry on transient failures
    llm_temperature: float = 0.3      # lower = more deterministic

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
