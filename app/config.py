"""Application configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    OPENAI_API_KEY: str = "test-openai-key"

    # Database Configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/contracts.db"

    # Application Settings
    APP_NAME: str = "Contract Clause Extractor"
    DEBUG: bool = True

    # JWT Configuration
    JWT_SECRET_KEY: str = "test-jwt-secret"  # Overridden in production via .env
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
