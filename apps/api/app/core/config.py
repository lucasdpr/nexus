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
    # Endereço público da API, usado no envio direto de arquivos grandes. Vazio desliga o
    # envio direto (o navegador usa o caminho normal, pelo front-end).
    public_api_url: str = ""
    # Definida pelo Render automaticamente.
    render_external_url: str = ""

    session_ttl_hours: int = 24 * 7
    login_window_minutes: int = 15
    login_max_failures_per_account_ip: int = 5
    login_max_failures_per_ip: int = 50
    login_max_failures_per_account: int = 20
    # Contas novas por IP (agrupado como nos logins) a cada hora, contando tentativas
    # recusadas também, para não servir de teste de quais e-mails já existem.
    signup_max_per_ip_per_hour: int = 5
    # Teto de contas novas por hora no sistema todo. Não depende de IP, então vale mesmo se alguém
    # forjar o endereço chamando a API direto, sem passar pelo front-end.
    signup_max_total_per_hour: int = 100
    # Quantos proxies confiáveis ficam entre o cliente e a API (lê o IP de X-Forwarded-For
    # a partir da direita). Sem valor: 4 em produção e 0 fora dela. O 4 foi medido em produção:
    # cliente, Vercel, Cloudflare (que fica na frente do Render) e o balanceador do Render.
    trusted_proxy_hops: int | None = None
    login_known_client_days: int = 30

    demo_enabled: bool = True
    demo_visitor_email: str = "visitante@novaforja.example.com"
    # Senha do administrador criado por `python -m app.cli seed-demo`; vazia gera uma aleatória.
    seed_admin_password: SecretStr | None = None

    # Arquivos enviados: disco local (desenvolvimento) ou serviço compatível com S3 (produção;
    # o disco de hospedagens gratuitas é apagado a cada reinício).
    # Sem valor: "db" em produção (arquivos no Postgres, duráveis sem configurar nada) e
    # "local" no desenvolvimento.
    storage_backend: Literal["local", "s3", "db"] | None = None
    storage_local_path: Path = API_DIR / "var" / "storage"
    s3_endpoint_url: str = ""
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: SecretStr | None = None
    s3_region: str = "auto"
    max_upload_mb: int = 25
    max_pdf_pages: int = 500

    # "hashing" roda localmente, sem custo, para testes e desenvolvimento sem chave de API.
    embedding_provider: Literal["voyage", "hashing"] = "hashing"
    voyage_api_key: SecretStr | None = None
    voyage_model: str = "voyage-4"

    # "extractive" responde sem modelo de linguagem (cita o trecho mais relevante): para
    # desenvolvimento e testes sem chave de API.
    answer_provider: Literal["gemini", "extractive"] = "extractive"
    gemini_api_key: SecretStr | None = None
    # gemini-3.8-flash é mais novo, mas não respondeu em 90 s no plano gratuito (out/2026).
    gemini_model: str = "gemini-3.5-flash"
    # Modelos tentados, em ordem, quando o principal responde 503 ou 429 (separados por vírgula).
    gemini_fallback_models: str = "gemini-3.8-flash"
    answer_max_output_tokens: int = 2048

    # Busca híbrida: candidatos de cada busca, fusão por posição e contexto enviado à IA.
    retrieval_vector_candidates: int = 40
    retrieval_text_candidates: int = 40
    retrieval_rrf_k: int = 60
    retrieval_max_sources: int = 8
    retrieval_min_similarity: float = 0.3
    retrieval_max_context_chars: int = 12000

    # Custo e abuso: perguntas por usuário por hora (a demonstração pública tem limite menor).
    chat_questions_per_hour: int = 60
    chat_demo_questions_per_hour: int = 15
    chat_max_question_chars: int = 1000

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
    def effective_storage_backend(self) -> Literal["local", "s3", "db"]:
        if self.storage_backend:
            return self.storage_backend
        return "db" if self.environment == "production" else "local"

    @property
    def direct_upload_url(self) -> str | None:
        base = (self.public_api_url or self.render_external_url).rstrip("/")
        return f"{base}/api/v1/documents/direct" if base else None

    @property
    def effective_proxy_hops(self) -> int:
        if self.trusted_proxy_hops is not None:
            return self.trusted_proxy_hops
        return 4 if self.environment == "production" else 0

    @property
    def cookie_secure(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
