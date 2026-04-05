from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "chatbot-service"
    environment: str = "dev"

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/chatbot_service"
    graph_core_base_url: str = "http://graph-core:8000"

    attachment_storage_path: str = "/tmp/chatbot-attachments"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()