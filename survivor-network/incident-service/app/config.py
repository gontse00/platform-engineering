from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    service_name: str = "incident-service"
    database_url: str = "postgresql+psycopg2://survivor:survivor-pw@survivor-db-postgresql.data.svc.cluster.local:5432/survivor"
    log_level: str = "INFO"
    graph_core_url: str = "http://graph-core:8080"
    participant_service_url: str = "http://participant-service:8080"
    notification_service_url: str = "http://notification-service:8080"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
