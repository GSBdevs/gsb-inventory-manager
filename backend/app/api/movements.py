from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.item import MovementBatchIn, MovementResultOut
from app.services.inventory_service import register_movement

router = APIRouter(prefix="/movements", tags=["movements"])


@router.post("", response_model=MovementResultOut, status_code=status.HTTP_201_CREATED)
async def create_movement(data: MovementBatchIn, db: DbSession, user: CurrentUser):
    try:
        return await register_movement(
            db, data.tipo, data.model_dump(), user.email
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from None
