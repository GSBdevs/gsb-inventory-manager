import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


def make_token(
    sub: str | None = None,
    email: str = "user@gruposb.com",
    aud: str = "authenticated",
    secret: str | None = None,
) -> str:
    """Emite um JWT no formato do Supabase, assinado com o secret de teste."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub or str(uuid.uuid4()),
        "email": email,
        "aud": aud,
        "role": "authenticated",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(payload, secret or settings.supabase_jwt_secret, algorithm="HS256")


def auth_headers(**kwargs) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(**kwargs)}"}
