"""
JDK Smart Factory Platform — Configuration
Environment-based settings for database, JWT auth, and application.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "JDK Smart Factory Platform"
    DEBUG: bool = True
    
    # Database
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "jdk_user"
    DATABASE_PASSWORD: str = "jdk_secure_password_2024"
    DATABASE_NAME: str = "jdk_smart_factory"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Security
    BCRYPT_ROUNDS: int = 12
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
