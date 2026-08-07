from typing import Any

import jwt

from app.core.config import settings

SUPABASE_ALGORITHM = "HS256"
SUPABASE_AUDIENCE = "authenticated"


def decode_supabase_jwt(token: str) -> dict[str, Any]:
    """Valida um JWT emitido pelo Supabase Auth (HS256 com o JWT secret do projeto).

    Levanta jwt.InvalidTokenError (inclui ExpiredSignatureError/InvalidAudienceError)
    quando o token é inválido, expirado ou tem audiência diferente de 'authenticated'.
    """
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=[SUPABASE_ALGORITHM],
        audience=SUPABASE_AUDIENCE,
    )
