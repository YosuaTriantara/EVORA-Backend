from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Category Schemas
# ---------------------------------------------------------------------------


class CategoryCreate(BaseModel):
    name: str = Field(..., description="Category name")
    event_id: UUID
    max_quota: int = Field(default=0, ge=0)
    registration_fee: float = Field(default=0.0, ge=0)


class CategoryRead(BaseModel):
    id: UUID
    name: str
    event_id: UUID
    max_quota: int
    registration_fee: float

    class Config:
        from_attributes = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    max_quota: Optional[int] = Field(default=None, ge=0)
    registration_fee: Optional[float] = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# Assessment Schemas (hierarchical: Section > Group > Item)
# ---------------------------------------------------------------------------


class AssessmentItemSchema(BaseModel):
    label: str
    display_number: int
    allowed_values: List[int] = Field(
        ..., description="Discrete allowed values, e.g. [0, 5, 10, 15]"
    )


class AssessmentItemRead(AssessmentItemSchema):
    id: UUID

    class Config:
        from_attributes = True


class AssessmentGroupSchema(BaseModel):
    title: str
    sort_order: Optional[int] = None
    items: List[AssessmentItemSchema]


class AssessmentGroupRead(BaseModel):
    id: UUID
    title: str
    sort_order: Optional[int] = None
    items: List[AssessmentItemRead] = []

    class Config:
        from_attributes = True


class AssessmentSectionSchema(BaseModel):
    title: str
    weight_percentage: int = Field(..., ge=1, le=100)
    sort_order: Optional[int] = None
    groups: List[AssessmentGroupSchema]


class AssessmentSectionRead(BaseModel):
    id: UUID
    title: str
    weight_percentage: int
    sort_order: Optional[int] = None
    groups: List[AssessmentGroupRead] = []

    class Config:
        from_attributes = True


class EventSchemaUpload(BaseModel):
    """Full assessment schema payload for SuperAdmin/Organizer upload (Spec 4.7)"""

    category_id: UUID
    sections: List[AssessmentSectionSchema]


class EventSchemaRead(BaseModel):
    category_id: UUID
    sections: List[AssessmentSectionRead] = []


# ---------------------------------------------------------------------------
# Event Staff (EventUser) Schemas
# ---------------------------------------------------------------------------

VALID_EVENT_ROLES = ["ORGANIZER", "JUDGE", "TABULATOR", "OFFICIAL_TEAM"]


class EventStaffCreate(BaseModel):
    user_id: UUID
    role: str = Field(
        ...,
        description="One of: ORGANIZER, JUDGE, TABULATOR, OFFICIAL_TEAM",
    )
    meta_data: Optional[Dict[str, Any]] = None


class EventStaffRead(BaseModel):
    id: UUID
    user_id: UUID
    event_id: UUID
    role: str
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserBasicInfo(BaseModel):
    """Basic user info for staff listings."""

    id: UUID
    email: str
    full_name: str

    class Config:
        from_attributes = True


class EventStaffReadWithUser(EventStaffRead):
    """Event staff with nested user information."""

    user: UserBasicInfo

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Event Schemas
# ---------------------------------------------------------------------------


class NavbarLink(BaseModel):
    label: str
    url: str


class EventBase(BaseModel):
    title: str = Field(..., description="Event name")
    slug: str = Field(..., description="Unique URL-friendly alias")
    organizer: str
    location: Optional[str] = None
    profil_url: Optional[str] = None
    content_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    theme_setting: Optional[Dict[str, Any]] = Field(default_factory=dict)
    event_date_start: date
    event_date_end: date
    is_voting_enabled: Optional[bool] = False
    stage: Optional[str] = Field(default=None)

class EventCreate(EventBase):
    pass

class EventRead(BaseModel):
    id: UUID
    title: str
    slug: str
    stage: Optional[str] = None
    organizer: Optional[str] = None
    location: Optional[str] = None
    profil_url: Optional[str] = None
    event_date_start: date
    event_date_end: date
    is_active: Optional[bool] = False
    is_pg_enabled: Optional[bool] = False
    is_voting_enabled: Optional[bool] = False
    content_data: Optional[Dict[str, Any]] = None
    theme_setting: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class EventReadFull(EventRead):
    categories: List[CategoryRead] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


class EventUpdate(BaseModel):
    """Full update schema for SuperAdmin — all fields optional"""

    title: Optional[str] = None
    slug: Optional[str] = None
    organizer: Optional[str] = None
    location: Optional[str] = None
    profil_url: Optional[str] = None
    event_date_start: Optional[date] = None
    event_date_end: Optional[date] = None
    is_active: Optional[bool] = None
    is_pg_enabled: Optional[bool] = None
    is_voting_enabled: Optional[bool] = None
    theme_setting: Optional[Dict[str, Any]] = None
    content_data: Optional[Dict[str, Any]] = None


class EventUpdateCustom(BaseModel):
    """Partial update for Organizer — only UI/content customisation"""

    title: Optional[str] = None
    slug: Optional[str] = None
    event_date_start: Optional[date] = None
    event_date_end: Optional[date] = None
    is_voting_enabled: Optional[bool] = None
    theme_settings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Theme/branding configuration",
        examples=[
            {
                "primary_color": "#000000",
                "secondary_color": "#FFFFFF",
                "font_family": "Arial, sans-serif",
                "navbar_style": "sticky",
                "header": {
                    "style": "sticky",
                    "background_color": "#ffffff",
                    "text_color": "#333333",
                },
                "footer": {
                    "background_color": "#1a1a1a",
                    "text_color": "#ffffff",
                },
            }
        ],
    )
    content_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Landing-page content configuration",
        examples=[
            {
                "navbar": {
                    "show_merchandise": True,
                    "show_categories": True,
                    "custom_links": [],
                },
                "hero": {
                    "title": "Welcome to EVORA",
                    "subtitle": "The Best Event Platform",
                    "banner_url": None,
                },
                "sections": {
                    "about": "Event description here...",
                    "judges": [],
                    "timeline": [],
                    "downloads": [],
                },
                "payment_config": {
                    "methods": ["MANUAL"],
                    "manual_instructions": {
                        "bank_name": "BCA",
                        "account_number": "123456789",
                        "account_holder": "Name Here",
                    },
                    "is_active": True,
                },
            }
        ],
    )


# ---------------------------------------------------------------------------
# Operation Response Schemas
# ---------------------------------------------------------------------------


class EventDeleteResponse(BaseModel):
    message: str
    event_id: UUID


class EventTogglePGResponse(BaseModel):
    """Response after toggling the Payment Gateway feature on an event."""

    message: str
    event_id: UUID
    is_pg_enabled: bool


class EventToggleVotingResponse(BaseModel):
    """Response after toggling the Voting feature on an event."""

    message: str
    event_id: UUID
    is_voting_enabled: bool


class EventToggleActiveResponse(BaseModel):
    """Response after toggling the active/published status of an event."""

    message: str
    event_id: UUID
    is_active: bool


class StaffRemoveResponse(BaseModel):
    """Response after removing a staff assignment from an event."""

    message: str
    event_user_id: UUID


class CategoryDeleteResponse(BaseModel):
    """Response after deleting a competition category."""

    message: str
    category_id: UUID


class SchemaUploadResponse(BaseModel):
    """Response after uploading an assessment schema for a category."""

    message: str
    category_id: UUID
    sections_count: int
