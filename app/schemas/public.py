from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.events import EventRead

# ---------------------------------------------------------------------------
# Event Catalogue (GET /public/events)
# ---------------------------------------------------------------------------


class EventPreview(BaseModel):
    """Lightweight event card used in the public catalogue listing."""

    id: UUID
    title: str
    slug: str
    organizer: Optional[str] = None
    profil_url: Optional[str] = None
    event_date_start: date
    event_date_end: date
    banner_url: Optional[str] = None
    is_registration_open: bool
    is_voting_live: Optional[bool] = False
    location: Optional[str] = None


# ---------------------------------------------------------------------------
# My Managed Events (GET /api/v1/events/my-managed)
# ---------------------------------------------------------------------------


class ManagedEventResponse(BaseModel):
    """Response schema for a single event assignment belonging to the current user."""

    role: str
    meta_data: Optional[Dict[str, Any]] = None
    event: EventPreview

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Landing Page — Registration Section
# ---------------------------------------------------------------------------


class CategorySlot(BaseModel):
    """Registration availability info per competition category."""

    id: UUID
    name: str
    fee: float
    max_quota: int
    available_slots: int
    is_full: bool


class RegistrationInfo(BaseModel):
    """Aggregated registration status for an event's landing page."""

    is_open: bool
    categories: List[CategorySlot] = []


# ---------------------------------------------------------------------------
# Landing Page — Voting Section
# ---------------------------------------------------------------------------


class CandidatePreview(BaseModel):
    """Public-facing voting candidate card."""

    team_name: str
    candidate_name: Optional[str] = None
    image_url: Optional[str] = None
    # None when real-time vote display is disabled in event config
    current_votes: Optional[int] = None


class VotingModule(BaseModel):
    """A single voting category with its candidates."""

    category_name: str
    candidates: List[CandidatePreview] = []


class VotingInfo(BaseModel):
    """Full voting block for the landing page."""

    # DISABLED | PREPARATION | LIVE | CLOSED
    status: str
    start_at: Optional[datetime] = None
    data: List[VotingModule] = []


# ---------------------------------------------------------------------------
# Landing Page — Full Response
# ---------------------------------------------------------------------------


class LandingPageResponse(BaseModel):
    """
    Complete data payload for an event's public landing page.

    ``event``         — core event details (title, dates, content, theme)
    ``registration``  — category slots and open/closed status
    ``voting``        — voting phase, candidates, and live tallies
    """

    event: EventRead
    registration: RegistrationInfo
    voting: VotingInfo

    class Config:
        from_attributes = True
