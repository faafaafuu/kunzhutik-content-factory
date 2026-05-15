from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Kunzhutik Content Factory", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_base_url: str = Field(default="http://localhost:8000", alias="APP_BASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    celery_broker_url: str = Field(alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(alias="CELERY_RESULT_BACKEND")

    s3_endpoint_url: str = Field(alias="S3_ENDPOINT_URL")
    s3_access_key: str = Field(alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(alias="S3_SECRET_KEY")
    s3_bucket: str = Field(alias="S3_BUCKET")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_secure: bool = Field(default=False, alias="S3_SECURE")

    telegram_bot_token: str | None = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_approval_chat_id: str | None = Field(default=None, alias="TELEGRAM_APPROVAL_CHAT_ID")
    telegram_approval_base_url: str | None = Field(default=None, alias="TELEGRAM_APPROVAL_BASE_URL")
    telegram_open_access: bool = Field(default=False, alias="TELEGRAM_OPEN_ACCESS")
    telegram_allowed_user_ids_raw: str = Field(default="", alias="TELEGRAM_ALLOWED_USER_IDS")

    dashboard_secret_key: str = Field(default="change-me-dashboard-secret", alias="DASHBOARD_SECRET_KEY")
    dashboard_cookie_name: str = Field(default="kunzhutik_dashboard_session", alias="DASHBOARD_COOKIE_NAME")
    dashboard_bootstrap_username: str | None = Field(default=None, alias="DASHBOARD_BOOTSTRAP_USERNAME")
    dashboard_bootstrap_password: str | None = Field(default=None, alias="DASHBOARD_BOOTSTRAP_PASSWORD")
    dashboard_bootstrap_role: str = Field(default="admin", alias="DASHBOARD_BOOTSTRAP_ROLE")

    vision_analysis_provider: str = Field(default="mock", alias="VISION_ANALYSIS_PROVIDER")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_vision_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_VISION_MODEL")
    openai_vision_detail: str = Field(default="low", alias="OPENAI_VISION_DETAIL")
    openai_vision_timeout_seconds: float = Field(default=45.0, alias="OPENAI_VISION_TIMEOUT_SECONDS")
    openai_vision_max_output_tokens: int = Field(default=900, alias="OPENAI_VISION_MAX_OUTPUT_TOKENS")

    default_project_slug: str = Field(default="kunzhutik-food", alias="DEFAULT_PROJECT_SLUG")
    default_project_name: str = Field(default="Kunzhutik Food Lab", alias="DEFAULT_PROJECT_NAME")
    default_character_name: str = Field(default="Кунжутик", alias="DEFAULT_CHARACTER_NAME")

    @property
    def telegram_allowed_user_ids(self) -> set[str]:
        return {
            item.strip()
            for item in self.telegram_allowed_user_ids_raw.split(",")
            if item.strip()
        }


settings = Settings()
