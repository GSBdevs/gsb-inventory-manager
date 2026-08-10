from fastapi import APIRouter

from app.api import auth, categories, technicians, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
api_router.include_router(technicians.router)
