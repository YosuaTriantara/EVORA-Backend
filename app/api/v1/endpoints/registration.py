import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.registration import (
    MemberCreate,
    MemberUpdate,
    MemberDeleteResponse,
    PaymentUploadResponse,
    PaymentVerifyResponse,
    TeamCreate,
    TeamLotUpdate,
    TeamLotUpdateResponse,
    TeamMemberRead,
    TeamRead,
    TeamRegisterResponse,
    TeamStatusUpdate,
    TeamStatusUpdateResponse,
    TeamUpdateResponse,
)
from app.services import registration as service

router = APIRouter()


@router.post(
    "/",
    response_model=TeamRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new team",
    tags=["Registration"],
)
def register_team(
    payload: TeamCreate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Register a new team for an event category.

    Atomically checks quota availability and reserves a slot.
    The team is created with status `PENDING_PAYMENT`.
    """
    return service.register_team(payload=payload, db=db, current_user=current_user)


@router.post(
    "/{team_id}/proof",
    response_model=PaymentUploadResponse,
    summary="Upload payment proof",
    tags=["Registration"],
)
async def upload_payment_proof(
    team_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Upload a payment proof file for a team.

    Transitions the team's status from `PENDING_PAYMENT` to `PENDING_VERIFICATION`.
    Only the team's official user may upload proof.
    """
    return await service.upload_payment_proof(
        team_id=team_id,
        file=file,
        db=db,
        current_user=current_user,
    )


@router.get(
    "/my-teams",
    response_model=List[TeamRead],
    summary="List my teams for an event",
    tags=["Registration"],
)
def get_my_teams(
    event_id: Optional[uuid.UUID] = None,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Return all teams the current user has registered as official.

    If `event_id` is provided, the result is filtered to that event.
    """
    return service.get_my_teams(event_id=event_id, db=db, current_user=current_user)


@router.patch(
    "/verify/{transaction_id}",
    response_model=PaymentVerifyResponse,
    summary="Verify or reject a registration payment",
    tags=["Registration"],
)
def verify_registration_payment(
    transaction_id: uuid.UUID,
    is_approved: bool,
    admin_note: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER", "SUPER_ADMIN"])),
):
    """
    Approve or reject a team's REGISTRATION payment transaction.

    - **Approve**: sets transaction to `PAID`, team to `REGISTERED`.
    - **Reject**: sets transaction to `FAILED`, team to `CANCELLED`.
    """
    return service.verify_registration_payment(
        transaction_id=transaction_id,
        is_approved=is_approved,
        admin_note=admin_note,
        db=db,
        current_user=current_user,
    )


@router.patch(
    "/{team_id}/update",
    response_model=TeamUpdateResponse,
    summary="Update team profile",
    tags=["Registration"],
)
def update_team(
    team_id: uuid.UUID,
    new_team_name: Optional[str] = None,
    new_institution: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["OFFICIAL_TEAM"])),
):
    """
    Update a team's display name or institution.

    Only the team's own official user (`OFFICIAL_TEAM`) may call this endpoint.
    """
    return service.update_team(
        team_id=team_id,
        new_team_name=new_team_name,
        new_institution=new_institution,
        db=db,
        current_user=current_user,
    )


@router.post(
    "/{team_id}/members",
    response_model=TeamMemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to a team",
    tags=["Registration"],
)
def add_team_member(
    team_id: uuid.UUID,
    payload: MemberCreate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Add a new member to the specified team.

    Use `extra_data` to supply supplemental info (email, phone, institution, etc.).
    """
    return service.add_team_member(
        team_id=team_id,
        member=payload,
        db=db,
        current_user=current_user,
    )


@router.get(
    "/{team_id}/members",
    response_model=List[TeamMemberRead],
    summary="List team members",
    tags=["Registration"],
)
def get_team_members(
    team_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Return all registered members belonging to a team.
    """
    return service.get_team_members(
        team_id=team_id,
        db=db,
        current_user=current_user,
    )


# ---------------------------------------------------------------------------
# Team Status & Lot Management (Event-Scoped for ORGANIZER)
# ---------------------------------------------------------------------------


@router.patch(
    "/{team_id}/status",
    response_model=TeamStatusUpdateResponse,
    summary="Update team status",
    tags=["Registration"],
)
def update_team_status(
    team_id: uuid.UUID,
    payload: TeamStatusUpdate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Update team status (event-scoped for ORGANIZER).
    
    **Allowed Status:** PENDING_PAYMENT, PENDING_VERIFICATION, REGISTERED, CANCELLED, DISQUALIFIED
    
    **Side Effects:**
    - If status changed to REGISTERED: creates transaction with status PAID
    - If status changed to CANCELLED/DISQUALIFIED: updates transaction to FAILED
    """
    return service.update_team_status(db=db, team_id=team_id, payload=payload)


@router.patch(
    "/{team_id}/lot",
    response_model=TeamLotUpdateResponse,
    summary="Update team lot number",
    tags=["Registration"],
)
def update_team_lot(
    team_id: uuid.UUID,
    payload: TeamLotUpdate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Update team lot number (event-scoped for ORGANIZER).
    
    **Validation:** lot_number must be >= 1 and unique within the category
    """
    return service.update_team_lot(db=db, team_id=team_id, payload=payload)


# ---------------------------------------------------------------------------
# Team Member Management (Event-Scoped for OFFICIAL_TEAM)
# ---------------------------------------------------------------------------


@router.patch(
    "/members/{member_id}",
    response_model=TeamMemberRead,
    summary="Update a team member",
    tags=["Registration"],
)
def update_team_member(
    member_id: uuid.UUID,
    payload: MemberUpdate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["OFFICIAL_TEAM"])),
):
    """
    Update a team member's details (event-scoped for OFFICIAL_TEAM).
    
    Only the team's official user can update members of their own team.
    """
    return service.update_team_member(
        member_id=member_id,
        payload=payload,
        db=db,
        current_user=current_user,
    )


@router.delete(
    "/members/{member_id}",
    response_model=MemberDeleteResponse,
    summary="Remove a team member",
    tags=["Registration"],
)
def delete_team_member(
    member_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["OFFICIAL_TEAM"])),
):
    """
    Remove a member from a team (event-scoped for OFFICIAL_TEAM).
    
    Only the team's official user can remove members from their own team.
    """
    return service.delete_team_member(
        member_id=member_id,
        db=db,
        current_user=current_user,
    )
