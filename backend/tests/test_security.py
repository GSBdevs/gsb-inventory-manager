from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import decode_supabase_jwt


def _token(secret: str, aud: str = "authenticated", exp_delta: int = 3600) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "user@gruposb.com",
        "aud": aud,
        "role": "authenticated",
        "iat": now,
        "exp": now + timedelta(seconds=exp_delta),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_decodes_valid_supabase_token():
    claims = decode_supabase_jwt(_token(settings.supabase_jwt_secret))
    assert claims["sub"] == "11111111-1111-1111-1111-111111111111"
    assert claims["email"] == "user@gruposb.com"


def test_rejects_wrong_secret():
    with pytest.raises(jwt.InvalidTokenError):
        decode_supabase_jwt(_token("outro-secret-invalido-000000000000"))


def test_rejects_wrong_audience():
    with pytest.raises(jwt.InvalidTokenError):
        decode_supabase_jwt(_token(settings.supabase_jwt_secret, aud="anon"))


def test_rejects_expired_token():
    with pytest.raises(jwt.InvalidTokenError):
        decode_supabase_jwt(_token(settings.supabase_jwt_secret, exp_delta=-10))


# --- Caminho assimétrico (ES256 via JWKS) — projetos com JWT signing keys ---


def _es256_token(private_key, aud: str = "authenticated", exp_delta: int = 3600) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": "22222222-2222-2222-2222-222222222222",
        "email": "es@gruposb.com",
        "aud": aud,
        "role": "authenticated",
        "iat": now,
        "exp": now + timedelta(seconds=exp_delta),
    }
    return jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": "test-kid"})


class _FakeSigningKey:
    def __init__(self, key):
        self.key = key


class _FakeJWKSClient:
    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, _token):
        return _FakeSigningKey(self._public_key)


def test_decodes_asymmetric_es256_via_jwks(monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import ec

    import app.core.security as security

    priv = ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setattr(security, "_jwks_client", lambda: _FakeJWKSClient(priv.public_key()))
    claims = security.decode_supabase_jwt(_es256_token(priv))
    assert claims["sub"] == "22222222-2222-2222-2222-222222222222"
    assert claims["email"] == "es@gruposb.com"


def test_rejects_es256_signed_by_unknown_key(monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import ec

    import app.core.security as security

    signer = ec.generate_private_key(ec.SECP256R1())
    other = ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setattr(security, "_jwks_client", lambda: _FakeJWKSClient(other.public_key()))
    with pytest.raises(jwt.InvalidTokenError):
        security.decode_supabase_jwt(_es256_token(signer))
