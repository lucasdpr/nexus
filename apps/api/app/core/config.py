from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# `.env` de apps/api, independentemente da pasta de onde o processo foi iniciado.
API_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Configuração lida de variáveis de ambiente (e de `.env` em desenvolvimento).

    Cada fase acrescenta apenas os campos que passa a usar.
    """

    model_config = SettingsConfigDict(
        env_file=API_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    database_url: SecretStr

    # Origem do front-end. Requisições que alteram dados vindas de outra origem são recusadas.
    web_origin: str = "http://localhost:3000"

    session_ttl_hours: int = 24 * 7
    login_window_minutes: int = 15
    login_max_failures_per_account_ip: int = 5
    login_max_failures_per_ip: int = 50
    login_max_failures_per_account: int = 20
    login_known_client_days: int = 30

    demo_enabled: bool = True
    demo_visitor_email: str = "visitante@novaforja.example.com"
    # Senha do administrador criado por `python -m app.cli seed-demo`; vazia gera uma aleatória.
    seed_admin_password: SecretStr | None = None

    @property
    def cookie_secure(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
