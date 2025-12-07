from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration"""

    # Database
    DATABASE_URL: str = "sqlite:///./crm.db"

    # Marktplaats
    MARKTPLAATS_CLIENT_ID: Optional[str] = None
    MARKTPLAATS_CLIENT_SECRET: Optional[str] = None
    MARKTPLAATS_REDIRECT_URI: str = "http://localhost:8000/auth/marktplaats/callback"
    MARKTPLAATS_API_BASE_URL: str = "https://api.marktplaats.nl/v1"

    # Vinted
    VINTED_EMAIL: Optional[str] = None
    VINTED_PASSWORD: Optional[str] = None
    VINTED_BASE_URL: str = "https://www.vinted.nl"

    # Depop
    DEPOP_USERNAME: Optional[str] = None
    DEPOP_PASSWORD: Optional[str] = None
    DEPOP_BASE_URL: str = "https://www.depop.com"

    # Facebook Marketplace
    FACEBOOK_EMAIL: Optional[str] = None
    FACEBOOK_PASSWORD: Optional[str] = None

    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = "credentials.json"
    GOOGLE_SHEETS_SPREADSHEET_ID: Optional[str] = None

    # Application
    SECRET_KEY: str = "change-this-to-a-random-secret-key"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Sync settings
    SYNC_INTERVAL_MINUTES: int = 15

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
