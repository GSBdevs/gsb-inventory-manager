from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.security import decode_supabase_jwt


def _token(secret: str, aud: str = "authenticated", exp_delta: int = 3600) -> str:
    now = datetime.now(timezone.utc)
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
