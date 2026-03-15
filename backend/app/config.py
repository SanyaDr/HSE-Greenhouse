from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Greenhouse Backend"
    database_url: str = "sqlite:///./backend/dev.db"
    jwt_secret: str = "replace_this_with_secure_random_value"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    frontend_allowed_origin: str | None = None
    thingsboard_url: str = ""
    thingsboard_token: str = ""
    thingsboard_device_check_path: str = "api/device/{serial_number}"
    thingsboard_username: str = ""
    thingsboard_password: str = ""
    thingsboard_login_path: str = "/api/auth/login"
    thingsboard_request_timeout: float = 10.0
    thingsboard_telemetry_path: str = "/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries"
    thingsboard_telemetry_keys: str = "temperature,humidity,actuatorOpen"
    thingsboard_telemetry_limit: int = 120
    automation_loop_enabled: bool = True
    ai_agent_enabled: bool = True
    ai_agent_loop_interval_seconds: int = 900
    ai_snapshot_window_minutes: int = 15
    ai_snapshot_interval_seconds: int = 300
    ai_recommendation_cooldown_minutes: int = 60
    ollama_base_url: str = "http://127.0.0.1:11434"
    ai_agent_model: str = "qwen3.5:cloud"
    ai_agent_temperature: float = 0.15
    ai_agent_max_tokens: int = 512
    ai_agent_system_prompt: str = (
        "Ты — агрономический ассистент, который анализирует телеметрию "
        "теплиц и формирует рекомендации по температуре, влажности и "
        "поливу. Дай краткое резюме обстановки, конкретные действия и "
        "прогноз рисков на ближайшие часы. Пиши по-русски."
    )

    class Config:
        env_file = Path(__file__).resolve().parents[1] / ".env"
        env_file_encoding = "utf-8"
