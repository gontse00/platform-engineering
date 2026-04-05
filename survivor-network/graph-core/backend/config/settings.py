from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "graph-core"
    app_env: str = "local"
    database_url: str = "postgresql://survivor:survivor-pw@localhost:5432/survivor"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()