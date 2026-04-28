from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    service_name: str = "participant-service"
    database_url: str = "postgresql+psycopg2://survivor:survivor-pw@survivor-db-postgresql.data.svc.cluster.local:5432/survivor"
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
