from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.events import EventSchemaRead
from app.services import superadmin as superadmin_service

router = APIRouter()


@router.get(
    "/{category_id}/schema",
    response_model=EventSchemaRead,
    summary="Get assessment schema for a category",
    tags=["Categories"],
)
def get_category_schema(
    category_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["JUDGE", "TABULATOR"])),
):
    """
    Retrieve the full nested assessment schema for a category.

    **Auth:** Required
    **Permission:** JUDGE, TABULATOR (event-scoped)
    """
    return superadmin_service.get_assessment_schema(db, category_id)
