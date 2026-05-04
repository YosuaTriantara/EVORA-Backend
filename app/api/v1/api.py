from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    categories,
    events,
    public,
    registration,
    scoring,
    superadmin,
    users,
    voting,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(categories.router, prefix="/categories", tags=["Categories"])
api_router.include_router(events.router, prefix="/events", tags=["Events"])
api_router.include_router(scoring.router, prefix="/scoring", tags=["Scoring"])
api_router.include_router(
    registration.router, prefix="/registration", tags=["Registration"]
)
api_router.include_router(public.router, prefix="/public", tags=["Public"])
api_router.include_router(voting.router, prefix="/voting", tags=["Voting"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(superadmin.router, prefix="/superadmin", tags=["SuperAdmin"])
