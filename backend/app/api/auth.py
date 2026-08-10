from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.schemas.profile import ProfileOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=ProfileOut)
async def me(user: CurrentUser):
    """Perfil do usuário atual. Provisiona o registro em `profiles` no 1º acesso."""
    return user
