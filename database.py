"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://igris_business_pulse_user:ceTpp5bBtuS0IyaK66sj3C5Sieg5KmZ7@dpg-dajet35g1s2s73ag9ff0-a.oregon-postgres.render.com/igris_business_pulse"
    JWT_SECRET_KEY: str = "change-this-in-production"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change-this-in-production"
    FRONTEND_ORIGIN: str = "http://localhost:5500"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
