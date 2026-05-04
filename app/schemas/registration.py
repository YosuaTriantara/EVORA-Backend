from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Team Member Schemas
# ---------------------------------------------------------------------------

VALID_MEMBER_ROLES = ["CAPTAIN", "MEMBER", "COACH", "MANAGER"]

VALID_TEAM_STATUSES = [
    "PENDING_PAYMENT",
    "PENDING_VERIFICATION",
    "REGISTERED",
    "CANCELLED",
    "DISQUALIFIED",
]


class MemberCreate(BaseModel):
    name: str
    role: str = Field(..., description="e.g. CAPTAIN, MEMBER, COACH, MANAGER")
    identity_number: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional info such as email, phone, institution, etc.",
        examples=[{"email": "member@example.com", "phone": "08123456789"}],
    )


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    identity_number: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class TeamMemberRead(BaseModel):
    id: UUID
    team_id: UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MemberDeleteResponse(BaseModel):
    """Response schema for deleting a team member."""
    message: str
    member_id: UUID


# ---------------------------------------------------------------------------
# Team Schemas
# ---------------------------------------------------------------------------


class TeamCreate(BaseModel):
    event_id: UUID
    category_id: UUID
    team_name: str = Field(..., description="Name of the participating team")
    institution: Optional[str] = Field(
        default=None, description="School / university / organisation name"
    )


class TeamRead(BaseModel):
    id: UUID
    event_id: UUID
    category_id: UUID
    name: str
    institution: Optional[str] = None
    status: str
    lot_number: Optional[int] = None

    class Config:
        from_attributes = True


class TeamReadFull(TeamRead):
    official_user_id: UUID
    members: List[TeamMemberRead] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


class TeamStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        description=(
            "One of: PENDING_PAYMENT, PENDING_VERIFICATION, "
            "REGISTERED, CANCELLED, DISQUALIFIED"
        ),
    )


class TeamLotUpdate(BaseModel):
    lot_number: int = Field(..., ge=1, description="Lot / appearance number")


class TeamDetail(TeamRead):
    official_user_id: UUID


# ---------------------------------------------------------------------------
# Operation Response Schemas
# ---------------------------------------------------------------------------


class TeamRegisterResponse(BaseModel):
    """Response after successfully registering a team (slot reserved)."""

    message: str
    team_id: UUID


class PaymentUploadResponse(BaseModel):
    """Response after uploading payment proof for a team."""

    message: str


class PaymentVerifyResponse(BaseModel):
    """Response after an organizer approves or rejects a payment."""

    message: str
    new_status: str


class TeamStatusUpdateResponse(BaseModel):
    """Response after manually overriding a team's registration status."""

    message: str
    team_id: UUID
    new_status: str


class TeamLotUpdateResponse(BaseModel):
    """Response after assigning or updating a team's lot number."""

    message: str
    team_id: UUID
    lot_number: int


class TeamUpdateResponse(BaseModel):
    """Response after an official updates their team's profile."""

    message: str
    team: TeamRead


class TeamDeleteResponse(BaseModel):
    """Response after permanently deleting a team."""

    message: str
    team_id: UUID


class MemberDeleteResponse(BaseModel):
    """Response after removing a member from a team."""

    message: str
    member_id: UUID


# ---------------------------------------------------------------------------
# Transaction Schemas
# ---------------------------------------------------------------------------


class TransactionRead(BaseModel):
    """Transaction data for organizer view"""
    id: UUID
    user_id: UUID
    user_email: Optional[str] = None
    transaction_type: str
    amount: float
    status: str
    payment_proof_url: Optional[str] = None
    team_id: Optional[UUID] = None
    team_name: Optional[str] = None
    category_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    verified_by: Optional[UUID] = None
    verified_at: Optional[datetime] = None
    admin_note: Optional[str] = None

    class Config:
        from_attributes = True
