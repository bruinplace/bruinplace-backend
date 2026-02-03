import os
import sys
from typing import List, Optional
import json

from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    A .env file is REQUIRED - the application will not start without it.
    """

    # Database Configuration (all required, no defaults)
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # Environment
    ENVIRONMENT: str

    # Google OAuth (OIDC)
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    # Accept raw string (CSV or JSON) to avoid provider JSON parsing errors
    ALLOWED_GOOGLE_HD: Optional[str] = None

    # App JWT settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from individual components."""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def allowed_google_domains(self) -> List[str]:
        """Parsed allowed domains. Supports CSV or JSON string; defaults to UCLA domains."""
        raw = self.ALLOWED_GOOGLE_HD
        if not raw:
            return ["ucla.edu", "g.ucla.edu"]
        s = raw.strip()
        # Try JSON array first
        if s.startswith("[") and s.endswith("]"):
            try:
                arr = json.loads(s)
                return [str(item).strip() for item in arr if str(item).strip()]
            except Exception:
                pass
        # Fallback: CSV
        return [item.strip() for item in s.split(",") if item.strip()]


def load_settings() -> Settings:
    """Load settings, raising an error if the .env file is missing or invalid."""
    try:
        return Settings()
    except ValidationError as e:
        if os.path.exists(".env"):
            print("\n❌ ERROR: .env file is invalid!\n")
            for err in e.errors():
                loc = ".".join(str(p) for p in err.get("loc", []))
                msg = err.get("msg", "")
                print(f" - {loc}: {msg}")
            print("\nPlease check your .env file and try again.\n")
        else:
            print(
                "\n❌ ERROR: .env file not found!\n\n" "Please create a .env file in the project root.\n"
            )
        sys.exit(1)


settings = load_settings()
