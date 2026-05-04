from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.common import PaginatedResponse
from app.schemas.events import (
    CategoryCreate,
    CategoryDeleteResponse,
    CategoryRead,
    CategoryUpdate,
    EventCreate,
    EventDeleteResponse,
    EventReadFull,
    EventSchemaRead,
    EventSchemaUpload,
    EventStaffCreate,
    EventStaffRead,
    EventToggleActiveResponse,
    EventTogglePGResponse,
    EventToggleVotingResponse,
    EventUpdate,
    SchemaUploadResponse,
    StaffRemoveResponse,
)
from app.schemas.registration import (
    MemberCreate,
    MemberDeleteResponse,
    MemberUpdate,
    TeamDeleteResponse,
    TeamLotUpdate,
    TeamLotUpdateResponse,
    TeamMemberRead,
    TeamReadFull,
    TeamStatusUpdate,
    TeamStatusUpdateResponse,
)
from app.schemas.scoring import (
    CategoryRankingRead,
    ScoreSheetLockResponse,
    ScoreSheetRead,
)
from app.schemas.transaction import (
    DashboardStats,
    TransactionRead,
    TransactionVerify,
    TransactionVerifyResponse,
)
from app.schemas.user import (
    UserAdminCreate,
    UserDeleteResponse,
    UserReadFull,
    UserUpdate,
)
from app.schemas.voting import (
    VoteCandidateCreate,
    VoteCandidateDeleteResponse,
    VoteCandidateRead,
    VoteCandidateUpdate,
    VoteCategoryCreate,
    VoteCategoryDeleteResponse,
    VoteCategoryRead,
    VoteCategoryUpdate,
    VotePackageCreate,
    VotePackageDeleteResponse,
    VotePackageRead,
    VotePackageUpdate,
)
from app.services import superadmin as service

router = APIRouter()

# ===========================================================================
# DASHBOARD
# ===========================================================================


@router.get(
    "/dashboard",
    response_model=DashboardStats,
    summary="Platform-wide statistics dashboard",
    tags=["SuperAdmin - Dashboard"],
)
def get_dashboard(
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Returns aggregate statistics for the entire platform:
    total users, events, teams, revenue, pending transactions, and per-event breakdowns.
    """
    return service.get_dashboard_stats(db)


# ===========================================================================
# USER MANAGEMENT
# ===========================================================================


@router.get(
    "/users",
    response_model=PaginatedResponse[UserReadFull],
    summary="List all users",
    tags=["SuperAdmin - Users"],
)
def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    role: Optional[str] = Query(
        default=None, description="Filter by role: SUPER_ADMIN | USER"
    ),
    is_active: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Search by name or email"),
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Returns a paginated list of all registered users.

    **Query params:**
    - `skip` / `limit` — pagination
    - `role` — filter by system role (`SUPER_ADMIN`, `USER`)
    - `is_active` — filter by account status
    - `search` — partial match on full_name or email
    """
    return service.get_users(
        db, skip=skip, limit=limit, role=role, is_active=is_active, search=search
    )


@router.get(
    "/users/{user_id}",
    response_model=UserReadFull,
    summary="Get a single user",
    tags=["SuperAdmin - Users"],
)
def get_user(
    user_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Get full details of a single user including timestamps and soft-delete status."""
    return service.get_user(db, user_id)


@router.post(
    "/users",
    response_model=UserReadFull,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user (admin)",
    tags=["SuperAdmin - Users"],
)
def create_user(
    payload: UserAdminCreate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Create a new user account with an explicit role.

    **Allowed roles:** `USER`, `SUPER_ADMIN`

    Unlike the public `/auth/register` endpoint, this allows setting any role
    directly without going through the self-registration flow.
    """
    return service.create_user_by_admin(db, payload)


@router.patch(
    "/users/{user_id}",
    response_model=UserReadFull,
    summary="Update a user",
    tags=["SuperAdmin - Users"],
)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Partially update a user's profile.

    **Editable fields:** `full_name`, `role`, `is_active`, `point_balance`

    All fields are optional — send only the ones you want to change.
    """
    return service.update_user(db, user_id, payload)


@router.delete(
    "/users/{user_id}",
    response_model=UserDeleteResponse,
    summary="Soft-delete a user",
    tags=["SuperAdmin - Users"],
)
def delete_user(
    user_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Soft-delete a user by setting `deleted_at` and deactivating the account.

    SuperAdmin accounts cannot be deleted.
    """
    return service.delete_user(db, user_id)


# ===========================================================================
# EVENT MANAGEMENT
# ===========================================================================


@router.get(
    "/events",
    response_model=PaginatedResponse[EventReadFull],
    summary="List all events (admin view)",
    tags=["SuperAdmin - Events"],
)
def list_events(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Search by title or slug"),
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Returns a paginated list of **all** events, including inactive/hidden ones.
    Supports filtering by active status and text search.
    """
    return service.get_all_events_admin(
        db, skip=skip, limit=limit, is_active=is_active, search=search
    )


@router.get(
    "/events/{event_id}",
    response_model=EventReadFull,
    summary="Get full event detail",
    tags=["SuperAdmin - Events"],
)
def get_event(
    event_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Get full event detail, including all nested categories."""
    return service.get_event_admin(db, event_id)


@router.post(
    "/events",
    response_model=EventReadFull,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event",
    tags=["SuperAdmin - Events"],
)
def create_event(
    payload: EventCreate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Create a brand-new event. The `slug` must be globally unique.

    After creation, use the staff management endpoints to assign organizers,
    judges, and other roles to this event.
    """
    return service.create_event_admin(db, payload)


@router.patch(
    "/events/{event_id}",
    response_model=EventReadFull,
    summary="Update an event",
    tags=["SuperAdmin - Events"],
)
def update_event(
    event_id: UUID,
    payload: EventUpdate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Partially update any field on an event.

    All fields are optional — send only the ones you want to change.
    Slug uniqueness is validated automatically.
    """
    return service.update_event(db, event_id, payload)


@router.delete(
    "/events/{event_id}",
    response_model=EventDeleteResponse,
    summary="Deactivate / soft-delete an event",
    tags=["SuperAdmin - Events"],
)
def delete_event(
    event_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Deactivate an event by setting `is_active = false`.
    The event is **not** permanently removed from the database.
    """
    return service.delete_event(db, event_id)


@router.patch(
    "/events/{event_id}/toggle-pg",
    response_model=EventTogglePGResponse,
    summary="Toggle Payment Gateway feature",
    tags=["SuperAdmin - Events"],
)
def toggle_event_pg(
    event_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Toggle `is_pg_enabled` on/off for an event."""
    return service.toggle_event_pg(db, event_id)


@router.patch(
    "/events/{event_id}/toggle-voting",
    response_model=EventToggleVotingResponse,
    summary="Toggle Voting feature",
    tags=["SuperAdmin - Events"],
)
def toggle_event_voting(
    event_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Toggle `is_voting_enabled` on/off for an event."""
    return service.toggle_event_voting(db, event_id)


@router.patch(
    "/events/{event_id}/toggle-active",
    response_model=EventToggleActiveResponse,
    summary="Toggle event active/published status",
    tags=["SuperAdmin - Events"],
)
def toggle_event_active(
    event_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Toggle `is_active` on/off — controls public visibility of the event."""
    return service.toggle_event_active(db, event_id)


# ===========================================================================
# EVENT STAFF MANAGEMENT
# ===========================================================================


@router.get(
    "/events/{event_id}/staff",
    response_model=List[EventStaffRead],
    summary="List event staff assignments",
    tags=["SuperAdmin - Event Staff"],
)
def list_event_staff(
    event_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    List all users assigned to an event and their roles.

    **Possible roles:** `ORGANIZER`, `JUDGE`, `TABULATOR`, `OFFICIAL_TEAM`
    """
    return service.get_event_staff(db, event_id)


@router.post(
    "/events/{event_id}/staff",
    response_model=EventStaffRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a user to an event role",
    tags=["SuperAdmin - Event Staff"],
)
def assign_event_staff(
    event_id: UUID,
    payload: EventStaffCreate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Assign an existing platform user to a role within an event.

    **Allowed roles:** `ORGANIZER`, `JUDGE`, `TABULATOR`, `OFFICIAL_TEAM`

    A user may hold multiple roles on the same event if needed.
    Duplicate role assignments are rejected.
    """
    return service.assign_event_staff(db, event_id, payload)


@router.delete(
    "/events/{event_id}/staff/{event_user_id}",
    response_model=StaffRemoveResponse,
    summary="Remove a staff assignment",
    tags=["SuperAdmin - Event Staff"],
)
def remove_event_staff(
    event_id: UUID,
    event_user_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Remove a specific role assignment from an event.
    The user account itself is not affected.
    """
    return service.remove_event_staff(db, event_user_id)


# ===========================================================================
# CATEGORY MANAGEMENT
# ===========================================================================


@router.get(
    "/events/{event_id}/categories",
    response_model=List[CategoryRead],
    summary="List categories for an event",
    tags=["SuperAdmin - Categories"],
)
def list_categories(
    event_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """List all competition categories registered under an event."""
    return service.get_categories(db, event_id)


@router.post(
    "/events/{event_id}/categories",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
    tags=["SuperAdmin - Categories"],
)
def create_category(
    event_id: UUID,
    payload: CategoryCreate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Create a new competition category for an event.

    **Fields:**
    - `name` — display name (e.g. `"PBB Variasi"`).
    - `max_quota` — maximum registrations allowed (`0` = unlimited).
    - `registration_fee` — fee in IDR.
    """
    return service.create_category(db, event_id, payload)


@router.patch(
    "/categories/{category_id}",
    response_model=CategoryRead,
    summary="Update a category",
    tags=["SuperAdmin - Categories"],
)
def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Partially update a category's name, quota, or registration fee."""
    return service.update_category(db, category_id, payload)


@router.delete(
    "/categories/{category_id}",
    response_model=CategoryDeleteResponse,
    summary="Delete a category",
    tags=["SuperAdmin - Categories"],
)
def delete_category(
    category_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Permanently delete a category and its entire assessment schema (cascade).

    **Guard:** Deletion is blocked if any active/registered teams exist in this category.
    """
    return service.delete_category(db, category_id)


# ===========================================================================
# ASSESSMENT SCHEMA MANAGEMENT
# ===========================================================================


@router.post(
    "/schema/upload",
    response_model=SchemaUploadResponse,
    summary="Upload / replace assessment schema",
    tags=["SuperAdmin - Assessment Schema"],
)
def upload_schema(
    payload: EventSchemaUpload,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Upload (or completely replace) the hierarchical assessment schema for a category.

    **Structure:** `Sections → Groups → Items`

    Each `Section` carries a `weight_percentage` (all sections should sum to 100).
    Each `Item` defines `allowed_values` — the discrete score values judges may enter
    (e.g. `[0, 5, 10, 15, 20]`).

    **Warning:** This operation **replaces** any existing schema for the category.
    Existing score sheets referencing old item IDs will be orphaned.
    """
    return service.upload_assessment_schema(db, payload)


@router.get(
    "/categories/{category_id}/schema",
    response_model=EventSchemaRead,
    summary="Get assessment schema for a category",
    tags=["SuperAdmin - Assessment Schema"],
)
def get_schema(
    category_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Retrieve the full nested assessment schema for a given category.

    Returns: `{ category_id, sections: [ { id, title, weight_percentage, groups: [...] } ] }`
    """
    return service.get_assessment_schema(db, category_id)


# ===========================================================================
# TEAM MANAGEMENT
# ===========================================================================


@router.get(
    "/events/{event_id}/teams",
    response_model=PaginatedResponse[TeamReadFull],
    summary="List all teams for an event",
    tags=["SuperAdmin - Teams"],
)
def list_teams(
    event_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status: Optional[str] = Query(
        default=None,
        description=(
            "Filter by status: PENDING_PAYMENT | PENDING_VERIFICATION | "
            "REGISTERED | CANCELLED | DISQUALIFIED"
        ),
    ),
    category_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    List all teams registered for an event with optional filters.

    **Query params:**
    - `status` — filter by registration status
    - `category_id` — filter by competition category
    - `skip` / `limit` — pagination
    """
    return service.get_teams_by_event(
        db,
        event_id=event_id,
        skip=skip,
        limit=limit,
        status=status,
        category_id=category_id,
    )


@router.get(
    "/teams/{team_id}",
    response_model=TeamReadFull,
    summary="Get team detail with members",
    tags=["SuperAdmin - Teams"],
)
def get_team(
    team_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Get full team info including all registered members."""
    return service.get_team_detail(db, team_id)


@router.patch(
    "/teams/{team_id}/status",
    response_model=TeamStatusUpdateResponse,
    summary="Update team registration status",
    tags=["SuperAdmin - Teams"],
)
def update_team_status(
    team_id: UUID,
    payload: TeamStatusUpdate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Manually override a team's registration status.

    **Valid statuses:**
    `PENDING_PAYMENT` → `PENDING_VERIFICATION` → `REGISTERED` → `CANCELLED` / `DISQUALIFIED`
    """
    return service.update_team_status(db, team_id, payload)


@router.patch(
    "/teams/{team_id}/lot",
    response_model=TeamLotUpdateResponse,
    summary="Assign lot number to a team",
    tags=["SuperAdmin - Teams"],
)
def update_team_lot(
    team_id: UUID,
    payload: TeamLotUpdate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Assign or update the performance/appearance lot number for a team.

    Lot numbers must be unique within the same competition category.
    """
    return service.update_team_lot(db, team_id, payload)


@router.delete(
    "/teams/{team_id}",
    response_model=TeamDeleteResponse,
    summary="Delete a team",
    tags=["SuperAdmin - Teams"],
)
def delete_team(
    team_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Permanently delete a team and all its members (cascades)."""
    return service.delete_team(db, team_id)


@router.get(
    "/teams/{team_id}/members",
    response_model=List[TeamMemberRead],
    summary="List team members",
    tags=["SuperAdmin - Teams"],
)
def list_team_members(
    team_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Get all members belonging to a specific team."""
    return service.get_team_members(db, team_id)


@router.post(
    "/teams/{team_id}/members",
    response_model=TeamMemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to a team",
    tags=["SuperAdmin - Teams"],
)
def add_team_member(
    team_id: UUID,
    payload: MemberCreate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Add a new member to any team.

    Use `extra_data` to store supplemental info such as email, phone, or institution.
    """
    return service.add_team_member_admin(db, team_id, payload)


@router.patch(
    "/members/{member_id}",
    response_model=TeamMemberRead,
    summary="Update a team member",
    tags=["SuperAdmin - Teams"],
)
def update_team_member(
    member_id: UUID,
    payload: MemberUpdate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Partially update a team member's name, role, identity number, or extra data."""
    return service.update_team_member(db, member_id, payload)


@router.delete(
    "/members/{member_id}",
    response_model=MemberDeleteResponse,
    summary="Remove a team member",
    tags=["SuperAdmin - Teams"],
)
def delete_team_member(
    member_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Permanently remove a member from their team."""
    return service.delete_team_member(db, member_id)


# ===========================================================================
# TRANSACTION MANAGEMENT
# ===========================================================================


@router.get(
    "/transactions",
    response_model=PaginatedResponse[TransactionRead],
    summary="List all transactions",
    tags=["SuperAdmin - Transactions"],
)
def list_transactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(
        default=None, description="PENDING | PAID | FAILED | REFUNDED"
    ),
    transaction_type: Optional[str] = Query(
        default=None, description="REGISTRATION | VOTE_PURCHASE | REFUND"
    ),
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    List all platform transactions with optional status and type filters.
    Results are ordered by `created_at` descending (newest first).
    """
    return service.get_all_transactions(
        db, skip=skip, limit=limit, status=status, transaction_type=transaction_type
    )


@router.get(
    "/events/{event_id}/transactions",
    response_model=PaginatedResponse[TransactionRead],
    summary="List transactions for an event",
    tags=["SuperAdmin - Transactions"],
)
def list_event_transactions(
    event_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    List all REGISTRATION transactions for a specific event,
    identified by `metadata.event_id`.
    """
    return service.get_event_transactions(
        db, event_id=event_id, skip=skip, limit=limit, status=status
    )


@router.patch(
    "/transactions/{transaction_id}/verify",
    response_model=TransactionVerifyResponse,
    summary="Approve or reject a payment",
    tags=["SuperAdmin - Transactions"],
)
def verify_transaction(
    transaction_id: UUID,
    payload: TransactionVerify,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Approve or reject a pending REGISTRATION payment.

    - **Approve** (`is_approved: true`): sets transaction to `PAID`, team to `REGISTERED`.
    - **Reject** (`is_approved: false`): sets transaction to `FAILED`, team to `CANCELLED`.
      `admin_note` is **required** when rejecting.
    """
    return service.verify_transaction(db, transaction_id, payload)


# ===========================================================================
# VOTE PACKAGE MANAGEMENT
# ===========================================================================


@router.get(
    "/vote-packages",
    response_model=List[VotePackageRead],
    summary="List all vote packages",
    tags=["SuperAdmin - Vote Packages"],
)
def list_vote_packages(
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """List all purchasable vote point packages, ordered by price ascending."""
    return service.get_vote_packages(db)


@router.post(
    "/vote-packages",
    response_model=VotePackageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a vote package",
    tags=["SuperAdmin - Vote Packages"],
)
def create_vote_package(
    payload: VotePackageCreate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Create a new purchasable vote points package.

    Example: `{ "name": "Paket Silver", "price_idr": 25000, "points_amount": 100 }`
    """
    return service.create_vote_package(db, payload)


@router.patch(
    "/vote-packages/{package_id}",
    response_model=VotePackageRead,
    summary="Update a vote package",
    tags=["SuperAdmin - Vote Packages"],
)
def update_vote_package(
    package_id: UUID,
    payload: VotePackageUpdate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Partially update a vote package's name, price, or points amount."""
    return service.update_vote_package(db, package_id, payload)


@router.delete(
    "/vote-packages/{package_id}",
    response_model=VotePackageDeleteResponse,
    summary="Delete a vote package",
    tags=["SuperAdmin - Vote Packages"],
)
def delete_vote_package(
    package_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Permanently delete a vote package. Does not affect past transactions."""
    return service.delete_vote_package(db, package_id)


# ===========================================================================
# VOTE CATEGORY MANAGEMENT
# ===========================================================================


@router.get(
    "/events/{event_id}/vote-categories",
    response_model=List[VoteCategoryRead],
    summary="List vote categories for an event",
    tags=["SuperAdmin - Vote Categories"],
)
def list_vote_categories(
    event_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    List all voting categories configured for an event
    (e.g. `"Danpas Terbaik"`, `"Kostum Terfavorit"`).
    """
    return service.get_vote_categories(db, event_id)


@router.post(
    "/events/{event_id}/vote-categories",
    response_model=VoteCategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a vote category",
    tags=["SuperAdmin - Vote Categories"],
)
def create_vote_category(
    event_id: UUID,
    payload: VoteCategoryCreate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Create a new voting category for an event.

    Optionally link it to a competition `EventCategory` via `target_event_category_id`
    to restrict candidates to teams registered in that category.
    """
    return service.create_vote_category(db, event_id, payload)


@router.patch(
    "/vote-categories/{vote_category_id}",
    response_model=VoteCategoryRead,
    summary="Update a vote category",
    tags=["SuperAdmin - Vote Categories"],
)
def update_vote_category(
    vote_category_id: UUID,
    payload: VoteCategoryUpdate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Partially update a voting category's name, description, or active status."""
    return service.update_vote_category(db, vote_category_id, payload)


@router.delete(
    "/vote-categories/{vote_category_id}",
    response_model=VoteCategoryDeleteResponse,
    summary="Delete a vote category",
    tags=["SuperAdmin - Vote Categories"],
)
def delete_vote_category(
    vote_category_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Delete a vote category. All associated candidates are also removed (cascade)."""
    return service.delete_vote_category(db, vote_category_id)


# ===========================================================================
# VOTE CANDIDATE MANAGEMENT
# ===========================================================================


@router.get(
    "/vote-categories/{vote_category_id}/candidates",
    response_model=List[VoteCandidateRead],
    summary="List candidates in a vote category",
    tags=["SuperAdmin - Vote Candidates"],
)
def list_vote_candidates(
    vote_category_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """List all voting candidates registered under a specific vote category."""
    return service.get_vote_candidates(db, vote_category_id)


@router.post(
    "/vote-categories/{vote_category_id}/candidates",
    response_model=VoteCandidateRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a candidate to a vote category",
    tags=["SuperAdmin - Vote Candidates"],
)
def add_vote_candidate(
    vote_category_id: UUID,
    payload: VoteCandidateCreate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Register a team as a candidate in a voting category.

    - `team_id` must reference an existing team.
    - `candidate_name` defaults to the team's name if omitted.
    - Duplicate entries (same team in same vote category) are rejected.
    """
    return service.add_vote_candidate(db, vote_category_id, payload)


@router.patch(
    "/vote-candidates/{candidate_id}",
    response_model=VoteCandidateRead,
    summary="Update a vote candidate",
    tags=["SuperAdmin - Vote Candidates"],
)
def update_vote_candidate(
    candidate_id: UUID,
    payload: VoteCandidateUpdate,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Update a candidate's display name or photo/banner image URL."""
    return service.update_vote_candidate(db, candidate_id, payload)


@router.delete(
    "/vote-candidates/{candidate_id}",
    response_model=VoteCandidateDeleteResponse,
    summary="Remove a vote candidate",
    tags=["SuperAdmin - Vote Candidates"],
)
def delete_vote_candidate(
    candidate_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """Permanently remove a candidate from a voting category. Vote logs are retained."""
    return service.delete_vote_candidate(db, candidate_id)


# ===========================================================================
# SCORE SHEET MANAGEMENT
# ===========================================================================


@router.get(
    "/events/{event_id}/scoresheets",
    response_model=List[ScoreSheetRead],
    summary="List score sheets for an event",
    tags=["SuperAdmin - Scoring"],
)
def list_score_sheets(
    event_id: UUID,
    category_id: Optional[UUID] = Query(
        default=None, description="Filter sheets to a specific competition category"
    ),
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    List all score sheets submitted for an event.

    Optionally filter by `category_id` to scope results to one competition category.
    Each sheet represents one judge's scores for one team.
    """
    return service.get_score_sheets(db, event_id=event_id, category_id=category_id)


@router.get(
    "/teams/{team_id}/scores",
    response_model=List[ScoreSheetRead],
    summary="Get all score sheets for a team",
    tags=["SuperAdmin - Scoring"],
)
def get_team_scores(
    team_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Retrieve every score sheet submitted for a team, including individual item values.

    Each sheet in the response contains a nested `items` list with per-criterion scores.
    """
    return service.get_team_scores(db, team_id)


@router.patch(
    "/scoresheets/{sheet_id}/lock",
    response_model=ScoreSheetLockResponse,
    summary="Lock a score sheet",
    tags=["SuperAdmin - Scoring"],
)
def lock_score_sheet(
    sheet_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Lock a score sheet to prevent any further edits.

    Once locked, neither the judge nor the tabulator can modify the scores.
    Use the `/unlock` endpoint below if a correction is needed.
    """
    return service.lock_score_sheet(db, sheet_id)


@router.patch(
    "/scoresheets/{sheet_id}/unlock",
    response_model=ScoreSheetLockResponse,
    summary="Unlock a score sheet (SuperAdmin override)",
    tags=["SuperAdmin - Scoring"],
)
def unlock_score_sheet(
    sheet_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Unlock a previously locked score sheet.

    **SuperAdmin only** — use this only to correct scoring errors.
    The judge/tabulator can then re-submit scores before locking again.
    """
    return service.unlock_score_sheet(db, sheet_id)


# ===========================================================================
# RANKINGS
# ===========================================================================


@router.get(
    "/events/{event_id}/categories/{category_id}/rankings",
    response_model=CategoryRankingRead,
    summary="Get final rankings for a category",
    tags=["SuperAdmin - Rankings"],
)
def get_category_rankings(
    event_id: UUID,
    category_id: UUID,
    db: Session = Depends(deps.get_db),
    _: deps.User = Depends(deps.get_super_admin),
):
    """
    Compute and return the final ranked standings for a competition category.

    **Scoring formula:** Average of all **locked** score sheets per team.

    **Tiebreaker:** Lower lot number wins on equal scores.

    Only locked sheets are included to guarantee finality.
    Teams with no locked sheets are included at the bottom with a score of 0.
    """
    return service.get_category_rankings(db, event_id=event_id, category_id=category_id)
