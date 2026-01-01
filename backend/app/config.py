import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    database_url: str = Field(default="mysql+aiomysql://app:app_password@127.0.0.1:3306/reservation")
    echo_sql: bool = Field(default=False)
    auth_secret: str = Field(..., description="Bearer token secret (required)")
    auth_algorithm: str = Field(default="HS256")


@lru_cache
def get_settings() -> Settings:
    auth_secret = os.getenv("AUTH_SECRET")
    if auth_secret is None:
        raise RuntimeError("AUTH_SECRET environment variable is required")
    return Settings(
        database_url=os.getenv("DATABASE_URL", Settings.model_fields["database_url"].default),
        echo_sql=bool(int(os.getenv("ECHO_SQL", "0"))),
        auth_secret=auth_secret,
        auth_algorithm=os.getenv("AUTH_ALGORITHM", Settings.model_fields["auth_algorithm"].default),
    )
