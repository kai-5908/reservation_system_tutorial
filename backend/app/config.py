from functools import lru_cache
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class Settings(BaseModel):
    database_url: str = Field(
        default="mysql+aiomysql://app:app_password@127.0.0.1:3306/reservation"
    )
    echo_sql: bool = Field(default=False)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", Settings.model_fields["database_url"].default),
        echo_sql=bool(int(os.getenv("ECHO_SQL", "0"))),
    )
