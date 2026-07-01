import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENVIRONMENT = os.getenv("APP_ENV", "development").strip().lower()

if ENVIRONMENT in {"development", "dev", "local"}:
    env_path = BASE_DIR / ".env.dev"
    if not env_path.exists():
        env_path = BASE_DIR / ".env"
elif ENVIRONMENT in {"production", "prod", "live"}:
    env_path = BASE_DIR / ".env"
else:
    env_path = BASE_DIR / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)


class Config:
    PROJECT_NAME: str = "FastAPI Testing"
    PROJECT_VERSION: str = "1.0.0"

    # Database
    POSTGRES_USER: str = os.getenv("DB_USER") or os.getenv("POSTGRES_USER") or "postgres"
    POSTGRES_PASSWORD: str = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD") or ""
    POSTGRES_SERVER: str = os.getenv("DB_SERVER") or os.getenv("POSTGRES_SERVER") or "localhost"
    POSTGRES_PORT: str = os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT") or "5432"
    POSTGRES_DB: str = os.getenv("DB_NAME") or os.getenv("POSTGRES_DB") or "tdd"

    DATABASE_URL: str = os.getenv("DATABASE_URL") or (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CHANGE_THIS_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")
    )

    # Session policy
    SINGLE_SESSION_LOGIN: bool = (
        os.getenv("SINGLE_SESSION_LOGIN", "true").lower() == "true"
    )

    # Login attempt policy
    MAX_FAILED_LOGIN_ATTEMPTS: int = int(
        os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5")
    )
    ACCOUNT_LOCK_MINUTES: int = int(
        os.getenv("ACCOUNT_LOCK_MINUTES", "15")
    )

    # Mail
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "").strip()
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "").replace(" ", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", MAIL_USERNAME).strip()
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.gmail.com").strip()
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))

    # ======== Cloudinary ====================================================
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
    CLOUDINARY_API_KEY:    str = os.getenv("CLOUDINARY_API_KEY",    "").strip()
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "").strip()

    # ======== Telegram Bot ==================================================
    TELEGRAM_BOT_TOKEN:    str = os.getenv("TELEGRAM_BOT_TOKEN",    "").strip()
    TELEGRAM_BOT_USERNAME: str = os.getenv("TELEGRAM_BOT_USERNAME", "").strip()

    # ======== Google Maps ===================================================
    GOOGLE_MAPS_API_KEY:   str = os.getenv("GOOGLE_MAPS_API_KEY",   "").strip()


configs = Config()
