from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATE_DIR = BASE_DIR / "app" / "templates"


class Settings(BaseSettings):
    app_name: str = "Whatsapp Havalandirma Bot"
    app_env: str = "development"
    database_url: str = "sqlite:///data/whatsapp_bot.sqlite3"
    public_base_url: str = ""
    admin_username: str = "admin"
    admin_password: str = ""

    whatsapp_verify_token: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_notify_phones: str = ""

    parasut_client_id: str = ""
    parasut_client_secret: str = ""
    parasut_username: str = ""
    parasut_password: str = ""
    parasut_company_id: str = "766184"
    parasut_redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob"

    default_currency: str = "TRL"
    default_vat_rate: int = 20
    default_offer_due_days: int = 7

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8-sig")


settings = Settings()


def sqlite_path() -> Path:
    if not settings.database_url.startswith("sqlite:///"):
        raise ValueError("Bu MVP sadece sqlite DATABASE_URL destekler.")
    raw_path = settings.database_url.replace("sqlite:///", "", 1)
    path = Path(raw_path)
    if not path.is_absolute():
        path = BASE_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
