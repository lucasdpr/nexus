from app.core.security import hash_password, hash_token, unusable_password_hash, verify_password


def test_password_hash_verifies_only_the_original_password() -> None:
    password_hash = hash_password("senha-segura-123")

    assert verify_password(password_hash, "senha-segura-123")
    assert not verify_password(password_hash, "senha-errada-000")


def test_missing_or_invalid_hash_never_verifies() -> None:
    assert not verify_password(None, "qualquer-coisa")
    assert not verify_password("isto-nao-e-um-hash", "qualquer-coisa")


def test_unusable_password_hash_rejects_guesses() -> None:
    assert not verify_password(unusable_password_hash(), "")


def test_session_token_hash_is_deterministic_sha256() -> None:
    assert hash_token("abc") == hash_token("abc")
    assert len(hash_token("abc")) == 32
    assert hash_token("abc") != hash_token("abd")
