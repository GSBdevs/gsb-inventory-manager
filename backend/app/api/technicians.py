from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models import Technician
from app.schemas.technician import TechnicianCreate, TechnicianOut

router = APIRouter(prefix="/technicians", tags=["technicians"])


@router.get("", response_model=list[TechnicianOut])
async def list_technicians(db: DbSession, _: CurrentUser):
    rows = await db.scalars(
        select(Technician).where(Technician.ativo.is_(True)).order_by(Technician.nome)
    )
    return list(rows)


@router.post("", response_model=TechnicianOut, status_code=201)
async def create_technician(data: TechnicianCreate, db: DbSession, _: CurrentUser):
    tech = Technician(nome=data.nome.strip())
    db.add(tech)
    await db.commit()
    await db.refresh(tech)
    return tech
