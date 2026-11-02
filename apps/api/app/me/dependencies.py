"""Dependencias de inyección del módulo ``me``."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.me.repository import MeRepository
from app.me.service import MeService


def get_me_service(session: AsyncSession = Depends(get_session)) -> MeService:
    return MeService(MeRepository(session))
