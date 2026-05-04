from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Score Item Schemas
# ---------------------------------------------------------------------------


class ScoreItemEntry(BaseModel):
    item_id: UUID
    val: int = Field(
        ..., description="Value must match allowed_values defined in assessment item"
    )


class ScoreItemRead(BaseModel):
    id: UUID
    sheet_id: UUID
    assessment_item_id: UUID
    value: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Score Sheet Schemas
# ---------------------------------------------------------------------------


class ScoringSubmit(BaseModel):
    team_id: UUID
    judge_id: UUID
    items: List[ScoreItemEntry]


class ScoreSheetRead(BaseModel):
    id: UUID
    team_id: UUID
    judge_id: UUID
    inputter_id: Optional[UUID] = None
    total_score: float
    is_locked: bool
    items: List[ScoreItemRead] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScoreSheetLockResponse(BaseModel):
    sheet_id: UUID
    is_locked: bool
    message: str


# ---------------------------------------------------------------------------
# Results / Rankings Schemas
# ---------------------------------------------------------------------------


class TeamRankEntry(BaseModel):
    rank: int
    team_id: UUID
    team_name: str
    lot_number: Optional[int] = None
    total_score: float
    judge_count: int


class CategoryRankingRead(BaseModel):
    event_id: UUID
    category_id: UUID
    category_name: str
    rankings: List[TeamRankEntry] = []


# ---------------------------------------------------------------------------
# Judge Assignment Schema (Spec 4.4)
# ---------------------------------------------------------------------------


class JudgeAssignment(BaseModel):
    event_id: UUID
    event_title: str
    category_name: str
    assigned_teams: List[dict]  # Contains team name and ID


# ---------------------------------------------------------------------------
# Score Submission Response
# ---------------------------------------------------------------------------


class ScoringSubmitResponse(BaseModel):
    """Response returned after a judge successfully submits or updates scores."""

    status: str
    total_score: float
    sheet_id: UUID


# ---------------------------------------------------------------------------
# Assessment Schema Schemas
# ---------------------------------------------------------------------------


class AssessmentItemRead(BaseModel):
    id: UUID
    label: str
    display_number: int
    allowed_values: List[int]

    class Config:
        from_attributes = True


class AssessmentGroupRead(BaseModel):
    id: UUID
    title: str
    sort_order: int
    items: List[AssessmentItemRead]

    class Config:
        from_attributes = True


class AssessmentSectionRead(BaseModel):
    id: UUID
    title: str
    weight_percentage: int
    sort_order: int
    groups: List[AssessmentGroupRead]

    class Config:
        from_attributes = True


class AssessmentSchemaRead(BaseModel):
    category_id: UUID
    sections: List[AssessmentSectionRead]

    class Config:
        from_attributes = True
