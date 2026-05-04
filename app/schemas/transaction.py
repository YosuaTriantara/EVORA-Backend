from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Transaction Schemas
# ---------------------------------------------------------------------------

VALID_TRANSACTION_TYPES = ["REGISTRATION", "VOTE_PURCHASE", "REFUND"]
VALID_TRANSACTION_STATUSES = ["PENDING", "PAID", "FAILED", "REFUNDED"]


class TransactionRead(BaseModel):
    id: UUID
    user_id: UUID
    transaction_type: str
    amount: float
    status: str
    payment_provider: Optional[str] = None
    external_ref_id: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransactionVerify(BaseModel):
    is_approved: bool = Field(..., description="True to approve, False to reject")
    admin_note: Optional[str] = Field(
        default=None,
        description="Required when rejecting; reason shown to the team official",
    )


class TransactionVerifyResponse(BaseModel):
    message: str
    transaction_id: UUID
    new_status: str
    team_id: Optional[UUID] = None


# ---------------------------------------------------------------------------
# Dashboard / Stats Schemas
# ---------------------------------------------------------------------------


class EventStats(BaseModel):
    event_id: UUID
    event_title: str
    slug: str
    total_teams: int
    registered_teams: int
    pending_payment_teams: int
    pending_verification_teams: int
    cancelled_teams: int
    total_revenue_idr: float
    is_active: bool


class DashboardStats(BaseModel):
    total_users: int
    total_active_users: int
    total_events: int
    total_active_events: int
    total_teams: int
    total_registered_teams: int
    total_revenue_idr: float
    total_pending_transactions: int
    total_vote_packages_sold: int
    events: List[EventStats] = []


class UserActivityStats(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    role: str
    total_teams: int
    point_balance: int
    total_votes_cast: int
    created_at: datetime
