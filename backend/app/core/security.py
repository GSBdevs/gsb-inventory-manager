from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError

from app.core.config import settings

SUPABASE_AUDIENCE = "authenticated"
# O Supabase pode assinar o token com o secret simétrico legado (HS256) OU com
# chaves assimétricas (ES256/RS256) publicadas no JWKS do projeto. Aceitamos ambos.
_ASYMMETRIC_ALGS = ["ES256", "RS256"]


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    return PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json")


def decode_supabase_jwt(token: str) -> dict[str, Any]:
    """Valida um JWT emitido pelo Supabase Auth.

    - HS256: verifica com o `SUPABASE_JWT_SECRET` (secret legado; usado nos testes).
    - ES256/RS256: verifica com a chave pública correspondente no JWKS do projeto
      (projetos que usam JWT signing keys assimétricas assinam os tokens de usuário assim).

    Levanta jwt.InvalidTokenError (inclui ExpiredSignatureError/InvalidAudienceError)
    quando o token é inválido, expirado ou tem audiência diferente de 'authenticated'.
    """
    alg = jwt.get_unverified_header(token).get("alg", "")
    if alg == "HS256":
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=SUPABASE_AUDIENCE,
        )
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
    except PyJWKClientError as exc:
        raise jwt.InvalidTokenError(f"Falha ao obter a chave do JWKS: {exc}") from exc
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=_ASYMMETRIC_ALGS,
        audience=SUPABASE_AUDIENCE,
    )
