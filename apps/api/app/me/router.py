"""Router ``me``: vistas transversales del usuario autenticado (solo auth)."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.me.dependencies import get_me_service
from app.me.schemas import MyProjectRead
from app.me.service import MeService
from app.models import User

router = APIRouter(prefix="/api/v1/me", tags=["me"])


@router.get("/projects", response_model=list[MyProjectRead])
async def my_projects(
    user: User = Depends(get_current_user),
    service: MeService = Depends(get_me_service),
) -> list[MyProjectRead]:
    """Proyectos accesibles por el usuario en todos sus workspaces, con su rol efectivo."""
    return await service.my_projects(user.user_id)
