from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.common import PaginatedResponse
from app.schemas.events import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    EventCreate,
    EventRead,
    EventReadFull,
    EventStaffCreate,
    EventStaffReadWithUser,
    EventUpdateCustom,
    StaffRemoveResponse,
    CategoryDeleteResponse,
)
from app.schemas.public import ManagedEventResponse
from app.schemas.registration import TeamReadFull, TransactionRead
from app.models.transaction import Transaction
from app.services import events as service
from app.services import superadmin as superadmin_service

router = APIRouter()


@router.get("/", response_model=List[EventRead])
def read_events(skip: int = 0, limit: int = 10, db: Session = Depends(deps.get_db)):

    return service.get_events(db, skip=skip, limit=limit)


@router.get("/my-managed", response_model=List[ManagedEventResponse])
def read_my_managed_events(
    db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_user)
):
    """
    Mengambil semua event aktif di mana user yang sedang login memiliki
    peran tertentu (ORGANIZER, JUDGE, TABULATOR, OFFICIAL_TEAM).
    Mendukung skenario multi-event: satu user bisa menjadi ORGANIZER di
    event A, JUDGE di event B, TABULATOR di event C secara bersamaan.
    """
    return service.get_user_managed_events(db, user_id=current_user.id)


@router.get("/by-id/{event_id}", response_model=EventReadFull)
def read_event_by_id(
    event_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(
        deps.EventRoleChecker(["ORGANIZER", "JUDGE", "TABULATOR", "OFFICIAL_TEAM"])
    ),
):
    """
    Get event details by ID for event-scoped roles.
    
    **Auth:** Required (Bearer Token)
    **Permission:** ORGANIZER, JUDGE, TABULATOR, OFFICIAL_TEAM (event-scoped)
    SuperAdmin can access all events.
    """
    return service.get_event_by_id(db, event_id=event_id)


@router.get("/{slug}", response_model=EventRead)
def read_event_by_slug(slug: str, db: Session = Depends(deps.get_db)):

    return service.get_event_by_slug(db, slug=slug)


@router.post("/create", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventCreate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_super_admin),
):

    return service.create_event(db, payload=payload)


@router.post("/categories", response_model=CategoryRead)
def create_category(
    event_id: UUID,
    payload: CategoryCreate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):

    return service.create_category(db, event_id=event_id, payload=payload)


@router.patch("/{event_id}/customize", response_model=EventRead)
def update_event_customization(
    event_id: UUID,
    payload: EventUpdateCustom,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):

    return service.update_event_customization(db, event_id=event_id, payload=payload)


# ---------------------------------------------------------------------------
# Event Staff Management (Event-Scoped)
# ---------------------------------------------------------------------------


@router.get("/{event_id}/staff", response_model=List[EventStaffReadWithUser])
def get_event_staff(
    event_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Get all staff members for an event.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    """
    return service.get_event_staff(db, event_id=event_id)


@router.post("/{event_id}/staff", response_model=EventStaffReadWithUser, status_code=status.HTTP_201_CREATED)
def add_event_staff(
    event_id: UUID,
    payload: EventStaffCreate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Add a staff member to an event.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    **Allowed Roles:** JUDGE, TABULATOR, OFFICIAL_TEAM (cannot assign ORGANIZER)
    """
    # Validate that role is not ORGANIZER
    if payload.role == "ORGANIZER":
        raise HTTPException(status_code=400, detail="Cannot assign ORGANIZER role via this endpoint")
    
    return service.add_event_staff(db, event_id=event_id, payload=payload)


@router.delete("/{event_id}/staff/{event_user_id}", response_model=StaffRemoveResponse)
def remove_event_staff(
    event_id: UUID,
    event_user_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Remove a staff member from an event.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    """
    return service.remove_event_staff(db, event_id=event_id, event_user_id=event_user_id)


# ---------------------------------------------------------------------------
# Category Management (Event-Scoped)
# ---------------------------------------------------------------------------


@router.patch("/categories/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Update event category.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped for categories in their events)
    """
    return service.update_category(db, category_id=category_id, payload=payload)


@router.delete("/categories/{category_id}", response_model=CategoryDeleteResponse)
def delete_category(
    category_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Delete event category.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    **Note:** Cannot delete category with active/registered teams
    """
    return service.delete_category(db, category_id=category_id)


@router.get(
    "/{event_id}/teams",
    response_model=PaginatedResponse[TeamReadFull],
    summary="List teams for an event",
    tags=["Events"],
)
def list_event_teams(
    event_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    List all teams registered for an event with optional filters.

    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    """
    return superadmin_service.get_teams_by_event(
        db,
        event_id=event_id,
        skip=skip,
        limit=limit,
        status=status,
        category_id=category_id,
    )


# ---------------------------------------------------------------------------
# Payment Verification & Transactions (Event-Scoped)
# ---------------------------------------------------------------------------



@router.get(
    "/{event_id}/transactions",
    response_model=PaginatedResponse[TransactionRead],
    summary="Get event transactions",
    tags=["Events"],
)
def get_event_transactions(
    event_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None, description="Filter: PENDING, PAID, FAILED, REFUNDED"),
    transaction_type: str | None = Query(default=None, description="Filter: REGISTRATION, VOTE_PURCHASE"),
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Get all transactions for an event (organizer-scoped).
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    
    **Query Parameters:**
    - `status`: Filter by transaction status
    - `transaction_type`: Filter by type
    """
    from app.models.registration import Team
    from app.models.event import EventCategory
    from app.models.user import User
    
    # Build base query with joins for additional info
    query = db.query(Transaction).join(
        Team, Transaction.team_id == Team.id
    ).join(
        EventCategory, Team.category_id == EventCategory.id
    ).filter(
        EventCategory.event_id == event_id
    )
    
    if status:
        query = query.filter(Transaction.status == status)
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    
    total = query.count()
    transactions = query.offset(skip).limit(limit).all()
    
    # Enrich with user and team info
    result = []
    for tx in transactions:
        team = db.query(Team).filter(Team.id == tx.team_id).first()
        user = db.query(User).filter(User.id == tx.user_id).first()
        category = None
        if team:
            category = db.query(EventCategory).filter(EventCategory.id == team.category_id).first()
        
        # Create enriched transaction data
        tx_data = {
            "id": tx.id,
            "user_id": tx.user_id,
            "user_email": user.email if user else None,
            "transaction_type": tx.transaction_type,
            "amount": tx.amount,
            "status": tx.status,
            "payment_proof_url": tx.meta_data.get("payment_proof_url") if tx.meta_data else None,
            "team_id": tx.team_id,
            "team_name": team.name if team else None,
            "category_name": category.name if category else None,
            "created_at": tx.created_at,
            "updated_at": tx.updated_at,
        }
        result.append(tx_data)
    
    return PaginatedResponse(
        total=total,
        skip=skip,
        limit=limit,
        data=result
    )


@router.patch(
    "/{event_id}/transactions/{transaction_id}/verify",
    summary="Verify payment",
    tags=["Events"],
)
def verify_payment(
    event_id: UUID,
    transaction_id: UUID,
    is_approved: bool,
    admin_note: str | None = None,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Verify or reject a payment transaction.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    
    **Side Effects:**
    - If approved: Transaction status -> PAID, Team status -> REGISTERED
    - If rejected: Transaction status -> FAILED, Team status -> CANCELLED
    """
    from app.models.registration import Team
    from app.models.event import EventCategory
    
    # Get transaction and verify it belongs to this event
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Verify transaction belongs to this event via team
    team = db.query(Team).filter(Team.id == transaction.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    category = db.query(EventCategory).filter(
        EventCategory.id == team.category_id,
        EventCategory.event_id == event_id
    ).first()
    
    if not category:
        raise HTTPException(status_code=403, detail="Transaction does not belong to this event")
    
    # Validate rejection note
    if not is_approved and (not admin_note or len(admin_note) < 10):
        raise HTTPException(
            status_code=400,
            detail="Admin note wajib diisi minimal 10 karakter untuk rejection"
        )
    
    # Verify transaction is pending
    if transaction.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Transaction already processed (status: {transaction.status})"
        )
    
    # Update transaction
    transaction.status = "PAID" if is_approved else "FAILED"
    transaction.verified_by = current_user.id
    transaction.verified_at = datetime.utcnow()
    transaction.admin_note = admin_note
    
    # Update team status
    if is_approved:
        team.status = "REGISTERED"
    else:
        team.status = "CANCELLED"
    
    db.commit()
    
    return {
        "message": "Verifikasi berhasil diproses",
        "transaction_id": transaction_id,
        "new_status": transaction.status,
        "team_id": team.id,
        "team_new_status": team.status,
        "verified_by": current_user.id,
        "verified_at": transaction.verified_at
    }


@router.get(
    "/{event_id}/transactions/{transaction_id}/proof",
    summary="View payment proof",
    tags=["Events"],
)
def view_payment_proof(
    event_id: UUID,
    transaction_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Get signed URL for payment proof (expires in 1 hour).
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    **Security:** URL signed with HMAC, expires 1 hour
    """
    from app.models.registration import Team
    from app.models.event import EventCategory
    
    # Get transaction and verify it belongs to this event
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Verify transaction belongs to this event
    team = db.query(Team).filter(Team.id == transaction.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    category = db.query(EventCategory).filter(
        EventCategory.id == team.category_id,
        EventCategory.event_id == event_id
    ).first()
    
    if not category:
        raise HTTPException(status_code=403, detail="Transaction does not belong to this event")
    
    # Get proof URL from metadata
    proof_url = None
    filename = None
    file_size = None
    if transaction.meta_data:
        proof_url = transaction.meta_data.get("payment_proof_url")
        filename = transaction.meta_data.get("filename")
        file_size = transaction.meta_data.get("file_size")
    
    if not proof_url:
        raise HTTPException(status_code=404, detail="No payment proof found")
    
    # Generate signed URL (simplified - in production use proper HMAC signing)
    import hashlib
    import time
    
    expires_at = datetime.utcnow().timestamp() + 3600  # 1 hour
    signature = hashlib.sha256(
        f"{transaction_id}:{expires_at}:secret".encode()
    ).hexdigest()
    
    signed_url = f"{proof_url}?signature={signature}&expires={int(expires_at)}"
    
    return {
        "transaction_id": transaction_id,
        "proof_url": signed_url,
        "expires_at": datetime.fromtimestamp(expires_at),
        "filename": filename or "bukti_transfer.jpg",
        "file_size": file_size or 0,
        "uploaded_at": transaction.created_at
    }
