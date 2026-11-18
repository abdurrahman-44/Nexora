"""NEXORA ERP — Core Configuration Module."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_SQLITE_PATH = (
    Path("/tmp/nexora_erp.db")
    if os.getenv("VERCEL")
    else BASE_DIR / "nexora_erp.db"
)


@dataclass
class Settings:
    app_name: str = os.getenv("APP_NAME", "NEXORA ERP")
    app_env: str = os.getenv("APP_ENV", "development")
    app_debug: bool = os.getenv("APP_DEBUG", "true").lower() == "true"
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "/api/v1")
    secret_key: str = os.getenv(
        "SECRET_KEY",
        "nexora-erp-enterprise-secret-key-2026-cryptographic-signing-key-998877",
    )
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Default Tenant Locale Settings
    default_org_name: str = os.getenv("DEFAULT_ORG_NAME", "Nexora Demo Holdings")
    default_currency: str = os.getenv("DEFAULT_CURRENCY", "LKR")
    default_timezone: str = os.getenv("DEFAULT_TIMEZONE", "Asia/Colombo")
    default_date_format: str = os.getenv("DEFAULT_DATE_FORMAT", "DD MMM YYYY")

    # Database URL: Uses PostgreSQL when configured/reachable, or persistent relational SQLite file in local dev
    database_url: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}",
    )

    # Redis & Celery
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

    # AI & LLM Provider
    llm_provider: str = os.getenv("NEXORA_LLM_PROVIDER", "local_analytical")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")

    # Security thresholds
    max_failed_login_attempts: int = 5
    lockout_minutes: int = 15
    po_dual_approval_threshold_lkr: float = 50000.00

    cors_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:8000",
            ).split(",")
            if origin.strip()
        ]
    )


settings = Settings()
