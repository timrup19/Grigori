"""
Application configuration using pydantic-settings.
"""

from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Grigori"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/prozorro_sentinel"
    DATABASE_ECHO: bool = False
    
    # Redis (optional)
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300  # 5 minutes
    
    # Prozorro API
    PROZORRO_API_BASE_URL: str = "https://public-api.prozorro.gov.ua/api/2.5"
    PROZORRO_API_TIMEOUT: int = 30
    PROZORRO_SYNC_BATCH_SIZE: int = 100

    # OpenSanctions API
    OPENSANCTIONS_API_URL: str = "https://api.opensanctions.org"
    OPENSANCTIONS_API_KEY: str = ""          # empty = no auth (non-commercial free tier)
    OPENSANCTIONS_BATCH_SIZE: int = 50       # max entities per match request
    OPENSANCTIONS_MIN_SCORE: float = 0.80    # minimum match score to flag as hit
    
    # EDR (Ukrainian company registry)
    EDR_API_URL: str = "https://api-sandbox.openprocurement.org/api/1.0/verify"
    EDR_TIMEOUT: int = 20
    EDR_ENABLED: bool = False   # flip to True once endpoint confirmed working

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://prozorro-sentinel.vercel.app",
    ]
    
    # Risk Scoring Thresholds
    RISK_THRESHOLD_MEDIUM: int = 25
    RISK_THRESHOLD_HIGH: int = 50
    RISK_THRESHOLD_CRITICAL: int = 75
    
    # Risk Weights (must sum to 1.0)
    RISK_WEIGHT_PRICE: float = 0.25
    RISK_WEIGHT_BID_PATTERN: float = 0.20
    RISK_WEIGHT_SINGLE_BIDDER: float = 0.20
    RISK_WEIGHT_NETWORK: float = 0.10
    RISK_WEIGHT_HIGH_VALUE: float = 0.05
    RISK_WEIGHT_SHORT_WINDOW: float = 0.10
    RISK_WEIGHT_AWARD_GAP: float = 0.10
    
    # Alerts
    ALERT_DAYS_DEFAULT: int = 7
    ALERT_MIN_RISK_SCORE: int = 50
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
