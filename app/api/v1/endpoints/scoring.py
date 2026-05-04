from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import crud_scoring
from app.schemas.scoring import (
    CategoryRankingRead,
    ScoreSheetLockResponse,
    ScoringSubmit,
    ScoringSubmitResponse,
)
from app.services import scoring as service

router = APIRouter()


@router.post(
    "/submit",
    response_model=ScoringSubmitResponse,
    summary="Submit or update scores for a team",
    tags=["Scoring"],
)
async def submit_score(
    payload: ScoringSubmit,
    db: Session = Depends(deps.get_db),
    _=Depends(deps.get_current_user),
):
    """
    Submit (or update) judge scores for a team.

    - Each ``item_id`` must reference a valid ``AssessmentItem``.
    - Each ``val`` must be one of the ``allowed_values`` defined on that item
      (discrete validation — e.g. only ``[0, 5, 10, 15, 20]`` are accepted).
    - If a score sheet already exists for this judge + team pair, the values
      are **updated in place** (idempotent).
    - A **locked** sheet cannot be modified; a 403 is returned.

    Returns the sheet ID and the recalculated total score.
    """
    return crud_scoring.process_score(db, payload=payload)


# ---------------------------------------------------------------------------
# Scoring Sheet Lock/Unlock (Event-Scoped for TABULATOR)
# ---------------------------------------------------------------------------


@router.patch(
    "/sheets/{sheet_id}/lock",
    response_model=ScoreSheetLockResponse,
    summary="Lock scoring sheet",
    tags=["Scoring"],
)
def lock_score_sheet(
    sheet_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["TABULATOR"])),
):
    """
    Lock a score sheet (event-scoped for TABULATOR).
    
    **Auth:** Required
    **Permission:** TABULATOR (event-scoped)
    """
    return service.lock_score_sheet(db, sheet_id=sheet_id)


@router.patch(
    "/sheets/{sheet_id}/unlock",
    response_model=ScoreSheetLockResponse,
    summary="Unlock scoring sheet",
    tags=["Scoring"],
)
def unlock_score_sheet(
    sheet_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["TABULATOR"])),
):
    """
    Unlock a score sheet (event-scoped for TABULATOR).
    
    **Auth:** Required
    **Permission:** TABULATOR (event-scoped)
    """
    return service.unlock_score_sheet(db, sheet_id=sheet_id)


# ---------------------------------------------------------------------------
# Rankings (Event-Scoped for ORGANIZER, JUDGE, TABULATOR)
# ---------------------------------------------------------------------------


@router.get(
    "/rankings",
    response_model=CategoryRankingRead,
    summary="Get category rankings",
    tags=["Scoring"],
)
def get_rankings(
    event_id: UUID,
    category_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER", "JUDGE", "TABULATOR"])),
):
    """
    Get rankings for a category (event-scoped).
    
    **Auth:** Required
    **Permission:** ORGANIZER, JUDGE, TABULATOR (event-scoped)
    
    **Query Parameters:**
    - `event_id`: Event UUID (required)
    - `category_id`: Category UUID (required)
    """
    return service.get_rankings(db, event_id=event_id, category_id=category_id)


# ---------------------------------------------------------------------------
# Assessment Schema (Event-Scoped for JUDGE, TABULATOR)
# ---------------------------------------------------------------------------

from app.schemas.scoring import AssessmentSchemaRead


@router.get(
    "/categories/{category_id}/schema",
    response_model=AssessmentSchemaRead,
    summary="Get assessment schema for a category",
    tags=["Scoring"],
)
def get_assessment_schema(
    category_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["JUDGE", "TABULATOR"])),
):
    """
    Get assessment schema for a category (event-scoped).
    
    **Auth:** Required
    **Permission:** JUDGE, TABULATOR (event-scoped for categories in their events)
    
    **Purpose:**
    - JUDGE uses this to see the scoring structure when filling score sheets
    - TABULATOR uses this for verification and troubleshooting
    - Schema is read-only for JUDGE/TABULATOR (only SuperAdmin can upload/update)
    """
    return service.get_assessment_schema(db, category_id=category_id)
