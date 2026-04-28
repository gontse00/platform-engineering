from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "admin-service"
    log_level: str = "INFO"
    auth_mode: str = "dev"
    request_timeout_seconds: int = 10

    graph_core_url: str = "http://graph-core:8080"
    incident_service_url: str = "http://incident-service:8080"
    participant_service_url: str = "http://participant-service:8080"
    attachment_service_url: str = "http://attachment-service:8080"
    notification_service_url: str = "http://notification-service:8080"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
