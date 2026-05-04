from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Vote Package Schemas
# ---------------------------------------------------------------------------


class VotePackageCreate(BaseModel):
    name: str = Field(..., description="Package display name (e.g., 'Paket Starter')")
    price_idr: int = Field(..., gt=0, description="Price in IDR")
    points_amount: int = Field(..., gt=0, description="Points granted on purchase")


class VotePackageRead(BaseModel):
    id: UUID
    name: str
    price_idr: int
    points_amount: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VotePackageUpdate(BaseModel):
    name: Optional[str] = None
    price_idr: Optional[int] = Field(default=None, gt=0)
    points_amount: Optional[int] = Field(default=None, gt=0)


class VotePackageDeleteResponse(BaseModel):
    """Response after deleting a vote package."""

    message: str
    package_id: UUID


# ---------------------------------------------------------------------------
# Vote Category Schemas
# ---------------------------------------------------------------------------


class VoteCategoryCreate(BaseModel):
    name: str = Field(..., description="Category name (e.g., 'Danpas Terbaik')")
    description: Optional[str] = Field(default=None, description="Category description")
    target_event_category_id: Optional[UUID] = Field(
        default=None, description="Optional: target specific event category"
    )
    is_active: bool = Field(default=True, description="Whether voting is active")


class VoteCategoryRead(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    description: Optional[str] = None
    target_event_category_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VoteCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_event_category_id: Optional[UUID] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Vote Candidate Schemas
# ---------------------------------------------------------------------------


class VoteCandidateCreate(BaseModel):
    vote_category_id: UUID
    team_id: UUID
    candidate_name: str = Field(..., description="Display name for the candidate")
    image_url: Optional[str] = Field(default=None, description="Candidate image URL")


class VoteCandidateRead(BaseModel):
    id: UUID
    vote_category_id: UUID
    team_id: UUID
    candidate_name: str
    image_url: Optional[str] = None
    total_votes: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VoteCandidateUpdate(BaseModel):
    candidate_name: Optional[str] = None
    image_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Operation Response Schemas
# ---------------------------------------------------------------------------


class VoteCategoryDeleteResponse(BaseModel):
    """Response after deleting a vote category."""

    message: str
    vote_category_id: UUID


class VoteCandidateDeleteResponse(BaseModel):
    """Response after deleting a vote candidate."""

    message: str
    candidate_id: UUID


# ---------------------------------------------------------------------------
# Public Vote Category Schemas (for public access)
# ---------------------------------------------------------------------------


class PublicVoteCategoryRead(BaseModel):
    """Public view of vote category with stats"""
    id: UUID
    name: str
    description: Optional[str] = None
    target_event_category_id: Optional[UUID] = None
    is_active: bool
    candidate_count: int = 0
    total_votes_cast: int = 0

    class Config:
        from_attributes = True


class PublicVoteCategoriesResponse(BaseModel):
    """Response for public vote categories endpoint"""
    event_id: UUID
    categories: List[PublicVoteCategoryRead]


# ---------------------------------------------------------------------------
# Public Vote Candidate Schemas (for public access)
# ---------------------------------------------------------------------------


class PublicVoteCandidateRead(BaseModel):
    """Public view of vote candidate with rank"""
    id: UUID
    team_id: UUID
    candidate_name: str
    image_url: Optional[str] = None
    display_order: int = 0
    total_votes: int = 0
    rank: int = 0
    last_vote_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PublicVoteCandidatesResponse(BaseModel):
    """Response for public vote candidates endpoint"""
    category_id: UUID
    event_id: UUID
    candidates: List[PublicVoteCandidateRead]
    total_votes_in_category: int = 0
    last_updated: datetime


# ---------------------------------------------------------------------------
# Vote Casting Schemas
# ---------------------------------------------------------------------------


class VoteCastRequest(BaseModel):
    """Request to cast a vote"""
    candidate_id: UUID
    points: int = Field(..., ge=1, description="Points to spend (min 1)")
    event_id: UUID


class VoteCastResponse(BaseModel):
    """Response after casting a vote"""
    message: str
    vote_id: UUID
    candidate_id: UUID
    points_deducted: int
    remaining_balance: int
    new_total_votes: int
    timestamp: datetime


# ---------------------------------------------------------------------------
# User Vote Balance Schemas
# ---------------------------------------------------------------------------


class UserVoteBalanceRead(BaseModel):
    """User vote balance for an event"""
    user_id: UUID
    event_id: UUID
    point_balance: int
    total_points_purchased: int
    total_points_spent: int
    last_purchase_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Vote History Schemas
# ---------------------------------------------------------------------------


class VoteHistoryItem(BaseModel):
    """Individual vote in history"""
    id: UUID
    candidate_id: UUID
    candidate_name: str
    category_name: str
    points: int
    created_at: datetime
    event_id: UUID

    class Config:
        from_attributes = True


class VoteHistoryResponse(BaseModel):
    """Paginated vote history response"""
    total: int
    skip: int
    limit: int
    data: List[VoteHistoryItem]


# ---------------------------------------------------------------------------
# Vote Purchase Schemas
# ---------------------------------------------------------------------------


class VotePurchaseRequest(BaseModel):
    """Request to purchase vote points"""
    package_id: UUID
    payment_method: str = Field(..., pattern="^(midtrans|xendit|manual_transfer)$")
    event_id: UUID


class VotePurchaseResponse(BaseModel):
    """Response after initiating vote purchase"""
    transaction_id: UUID
    package_id: UUID
    points_amount: int
    amount_idr: int
    status: str
    payment_provider: Optional[str] = None
    payment_token: Optional[str] = None
    redirect_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime


class VotePurchaseStatusResponse(BaseModel):
    """Response for checking purchase status"""
    transaction_id: UUID
    status: str  # PENDING, PAID, FAILED, EXPIRED
    package_id: UUID
    points_amount: int
    amount_idr: int
    paid_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    failure_reason: Optional[str] = None
    retry_available: bool


# ---------------------------------------------------------------------------
# SSE Vote Stream Schemas
# ---------------------------------------------------------------------------


class VoteUpdateEvent(BaseModel):
    """SSE event for vote update"""
    candidate_id: UUID
    new_total: int
    timestamp: datetime


class LeaderboardUpdateEvent(BaseModel):
    """SSE event for leaderboard update"""
    category_id: UUID
    top_3: List[PublicVoteCandidateRead]
    timestamp: datetime
