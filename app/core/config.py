import os
import sys
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError


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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from individual components."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


def load_settings() -> Settings:
    """
    Load settings, raising an error if the .env file is missing or invalid.
    """
    try:
        return Settings()
    except ValidationError as e:
        if os.path.exists(".env"):
            print(
                "\n❌ ERROR: .env file is invalid!\n\n"
                "Please check your .env file and try again.\n"
            )
        else:
            print(
                "\n❌ ERROR: .env file not found!\n\n"
                "Please create a .env file in the project root.\n"
            )
        sys.exit(1)


settings = load_settings()
