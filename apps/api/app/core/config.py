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

    # Arquivos enviados. Em produção, trocar por armazenamento compatível com S3.
    storage_local_path: Path = API_DIR / "var" / "storage"
    max_upload_mb: int = 25
    max_pdf_pages: int = 500

    # "hashing" roda localmente, sem custo, para testes e desenvolvimento sem chave de API.
    embedding_provider: Literal["voyage", "hashing"] = "hashing"
    voyage_api_key: SecretStr | None = None
    voyage_model: str = "voyage-4"

    # Tamanhos em caracteres (~4 caracteres por token em português).
    chunk_target_chars: int = 2000
    chunk_max_chars: int = 2600
    chunk_overlap_chars: int = 300

    # Em hospedagem gratuita, o worker pode rodar dentro do processo da API.
    run_worker_in_api: bool = False
    worker_poll_seconds: float = 2.0
    job_max_attempts: int = 3
    job_retry_base_seconds: float = 30.0
    job_stale_minutes: int = 15

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cookie_secure(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
