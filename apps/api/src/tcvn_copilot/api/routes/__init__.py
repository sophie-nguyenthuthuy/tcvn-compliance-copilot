"""API route registration."""

from __future__ import annotations

from fastapi import APIRouter

from tcvn_copilot.api.routes import auth, compliance, health, projects, standards, uploads

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(standards.router, prefix="/standards", tags=["standards"])
api_router.include_router(compliance.router, prefix="/compliance", tags=["compliance"])

__all__ = ["api_router"]
