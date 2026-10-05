import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

# Verificado quando o e-mail não existe, para o tempo de resposta não revelar contas.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except VerificationError, InvalidHashError:
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> bytes:
    """Só o hash do token vai para o banco; vazar a tabela não expõe sessões válidas."""
    return hashlib.sha256(token.encode()).digest()


def unusable_password_hash() -> str:
    """Hash de uma senha aleatória descartada: a conta existe, mas ninguém faz login por senha."""
    return _hasher.hash(secrets.token_urlsafe(32))
