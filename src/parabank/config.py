from __future__ import annotations

from functools import cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Адрес стенда и таймауты из переменных окружения PARABANK_*.

    По умолчанию — локальный Docker из docker-compose.yml. Публичный стенд:
    PARABANK_BASE_URL=https://parabank.parasoft.com/parabank
    """

    model_config = SettingsConfigDict(env_prefix="PARABANK_")

    base_url: str = "http://localhost:8090/parabank"
    timeout: float = 15.0

    @property
    def site_url(self) -> str:
        """Адрес для страниц UI: со слешем на конце, чтобы относительные пути вида overview.htm
        разрешались внутри /parabank/."""
        return self.base_url.rstrip("/") + "/"

    @property
    def api_url(self) -> str:
        return self.base_url.rstrip("/") + "/services/bank"


@cache
def get_settings() -> Settings:
    return Settings()
