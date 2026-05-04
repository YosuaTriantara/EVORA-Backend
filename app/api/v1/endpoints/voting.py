from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.voting import (
    VoteCategoryCreate,
    VoteCategoryDeleteResponse,
    VoteCategoryRead,
    VoteCategoryUpdate,
    VoteCandidateCreate,
    VoteCandidateDeleteResponse,
    VoteCandidateRead,
    VoteCandidateUpdate,
)
from app.services import voting as service

router = APIRouter()


# ---------------------------------------------------------------------------
# Vote Category Management (Event-Scoped)
# ---------------------------------------------------------------------------


@router.get(
    "/events/{event_id}/voting/categories",
    response_model=List[VoteCategoryRead],
    summary="Get vote categories for an event",
    tags=["Voting"],
)
def get_vote_categories(
    event_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Get all vote categories for an event.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    """
    return service.get_vote_categories(db, event_id=event_id)


@router.post(
    "/events/{event_id}/voting/categories",
    response_model=VoteCategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create vote category",
    tags=["Voting"],
)
def create_vote_category(
    event_id: UUID,
    payload: VoteCategoryCreate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Create a new vote category for an event.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    """
    return service.create_vote_category(db, event_id=event_id, payload=payload)


@router.patch(
    "/events/voting/categories/{vote_category_id}",
    response_model=VoteCategoryRead,
    summary="Update vote category",
    tags=["Voting"],
)
def update_vote_category(
    vote_category_id: UUID,
    payload: VoteCategoryUpdate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Update a vote category.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped for categories in their events)
    """
    return service.update_vote_category(db, vote_category_id=vote_category_id, payload=payload)


@router.delete(
    "/events/voting/categories/{vote_category_id}",
    response_model=VoteCategoryDeleteResponse,
    summary="Delete vote category",
    tags=["Voting"],
)
def delete_vote_category(
    vote_category_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Delete a vote category.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    """
    return service.delete_vote_category(db, vote_category_id=vote_category_id)


# ---------------------------------------------------------------------------
# Vote Candidate Management (Event-Scoped)
# ---------------------------------------------------------------------------


@router.get(
    "/events/voting/categories/{vote_category_id}/candidates",
    response_model=List[VoteCandidateRead],
    summary="Get vote candidates",
    tags=["Voting"],
)
def get_vote_candidates(
    vote_category_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Get all vote candidates for a category.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    """
    return service.get_vote_candidates(db, vote_category_id=vote_category_id)


@router.post(
    "/events/{event_id}/voting/candidates",
    response_model=VoteCandidateRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create vote candidate",
    tags=["Voting"],
)
def create_vote_candidate(
    event_id: UUID,
    payload: VoteCandidateCreate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Create a new vote candidate.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    """
    return service.create_vote_candidate(db, event_id=event_id, payload=payload)


@router.patch(
    "/events/voting/candidates/{candidate_id}",
    response_model=VoteCandidateRead,
    summary="Update vote candidate",
    tags=["Voting"],
)
def update_vote_candidate(
    candidate_id: UUID,
    payload: VoteCandidateUpdate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Update a vote candidate.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    """
    return service.update_vote_candidate(db, candidate_id=candidate_id, payload=payload)


@router.delete(
    "/events/voting/candidates/{candidate_id}",
    response_model=VoteCandidateDeleteResponse,
    summary="Delete vote candidate",
    tags=["Voting"],
)
def delete_vote_candidate(
    candidate_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Delete a vote candidate.
    
    **Auth:** Required
    **Permission:** ORGANIZER (event-scoped)
    """
    return service.delete_vote_candidate(db, candidate_id=candidate_id)


# ---------------------------------------------------------------------------
# Vote Casting (Authenticated Users)
# ---------------------------------------------------------------------------

from datetime import datetime
from fastapi import Header, HTTPException, Request
from app.schemas.voting import VoteCastRequest, VoteCastResponse
from app.models.transaction import Vote, UserVoteBalance, VoteCandidate
from sqlalchemy import func
import uuid


@router.post(
    "/votes/cast",
    response_model=VoteCastResponse,
    summary="Cast a vote",
    tags=["Voting"],
)
def cast_vote(
    request: Request,
    payload: VoteCastRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Cast a vote for a candidate.
    
    **Auth:** Required (JWT)
    **Idempotency:** Required (header `Idempotency-Key: {uuid}`)
    
    Atomic transaction: deducts balance and records vote.
    Rate limit: 5 votes per minute per user.
    """
    # Validate idempotency key format
    try:
        idem_key_uuid = uuid.UUID(idempotency_key)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid idempotency key format")
    
    # Check for duplicate idempotency key (24-hour retention)
    existing_vote = db.query(Vote).filter(
        Vote.idempotency_key == idem_key_uuid,
        Vote.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ).first()
    
    if existing_vote:
        # Return same response without double deduct
        candidate = db.query(VoteCandidate).filter(
            VoteCandidate.id == existing_vote.candidate_id
        ).first()
        
        balance = db.query(UserVoteBalance).filter(
            UserVoteBalance.user_id == current_user.id,
            UserVoteBalance.event_id == payload.event_id
        ).first()
        
        return VoteCastResponse(
            message="Vote already processed",
            vote_id=existing_vote.id,
            candidate_id=existing_vote.candidate_id,
            points_deducted=existing_vote.points,
            remaining_balance=balance.point_balance if balance else 0,
            new_total_votes=candidate.total_votes if candidate else 0,
            timestamp=existing_vote.created_at
        )
    
    # Check rate limit (5 votes per minute per user)
    one_minute_ago = datetime.utcnow().replace(second=0, microsecond=0)
    recent_votes = db.query(func.count(Vote.id)).filter(
        Vote.user_id == current_user.id,
        Vote.created_at >= one_minute_ago
    ).scalar()
    
    if recent_votes >= 5:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded: max 5 votes per minute"
        )
    
    # Verify candidate exists and is active
    candidate = db.query(VoteCandidate).filter(
        VoteCandidate.id == payload.candidate_id
    ).first()
    
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Verify candidate belongs to the event
    from app.models.transaction import VoteCategory
    category = db.query(VoteCategory).filter(
        VoteCategory.id == candidate.vote_category_id,
        VoteCategory.event_id == payload.event_id
    ).first()
    
    if not category:
        raise HTTPException(status_code=400, detail="Candidate does not belong to this event")
    
    if not category.is_active:
        raise HTTPException(status_code=400, detail="Voting is not active for this category")
    
    # Atomic transaction: lock balance, verify, deduct, insert vote
    try:
        # Lock the balance row
        balance = db.query(UserVoteBalance).filter(
            UserVoteBalance.user_id == current_user.id,
            UserVoteBalance.event_id == payload.event_id
        ).with_for_update().first()
        
        if not balance:
            raise HTTPException(status_code=400, detail="No vote balance found for this event")
        
        if balance.point_balance < payload.points:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Available: {balance.point_balance}, Required: {payload.points}"
            )
        
        # Deduct balance
        balance.point_balance -= payload.points
        balance.total_spent += payload.points
        
        # Create vote record
        vote = Vote(
            user_id=current_user.id,
            candidate_id=payload.candidate_id,
            event_id=payload.event_id,
            points=payload.points,
            idempotency_key=idem_key_uuid,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        db.add(vote)
        
        # Update candidate vote count
        candidate.total_votes += payload.points
        candidate.last_vote_at = datetime.utcnow()
        
        db.commit()
        db.refresh(vote)
        db.refresh(candidate)
        
        return VoteCastResponse(
            message="Vote berhasil dicatat",
            vote_id=vote.id,
            candidate_id=payload.candidate_id,
            points_deducted=payload.points,
            remaining_balance=balance.point_balance,
            new_total_votes=candidate.total_votes,
            timestamp=vote.created_at
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cast vote: {str(e)}")


# ---------------------------------------------------------------------------
# Vote Purchase (Initiate)
# ---------------------------------------------------------------------------

from datetime import timedelta
from app.schemas.voting import VotePurchaseRequest, VotePurchaseResponse
from app.models.transaction import VoteTransaction, VotePackage


@router.post(
    "/purchase",
    response_model=VotePurchaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Purchase vote points",
    tags=["Voting"],
)
def purchase_vote_points(
    payload: VotePurchaseRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Initiate purchase of vote points.
    
    **Auth:** Required
    **Idempotency:** Same user + package returns existing pending transaction
    
    Creates a pending transaction and returns payment provider details.
    """
    # Verify package exists and is active
    package = db.query(VotePackage).filter(
        VotePackage.id == payload.package_id,
        VotePackage.is_active == True
    ).first()
    
    if not package:
        raise HTTPException(status_code=404, detail="Vote package not found or inactive")
    
    # Check for existing pending transaction (idempotency)
    existing_tx = db.query(VoteTransaction).filter(
        VoteTransaction.user_id == current_user.id,
        VoteTransaction.package_id == payload.package_id,
        VoteTransaction.event_id == payload.event_id,
        VoteTransaction.status == "PENDING",
        VoteTransaction.expires_at > datetime.utcnow()
    ).first()
    
    if existing_tx:
        # Return existing transaction
        return VotePurchaseResponse(
            transaction_id=existing_tx.id,
            package_id=existing_tx.package_id,
            points_amount=existing_tx.points_amount,
            amount_idr=existing_tx.amount_idr,
            status=existing_tx.status,
            payment_provider=existing_tx.payment_provider,
            payment_token=existing_tx.payment_token,
            redirect_url=existing_tx.redirect_url,
            expires_at=existing_tx.expires_at,
            created_at=existing_tx.created_at
        )
    
    # Create new transaction
    expires_at = datetime.utcnow() + timedelta(minutes=60)
    
    # Generate idempotency key
    idem_key = uuid.uuid4()
    
    # Create payment token and redirect URL based on provider
    payment_token = None
    redirect_url = None
    
    if payload.payment_method == "midtrans":
        # Generate mock Midtrans token (in production, call Midtrans API)
        payment_token = f"midtrans-snap-token-{uuid.uuid4().hex[:16]}"
        redirect_url = f"https://app.midtrans.com/snap/v2/vtweb/{payment_token}"
    elif payload.payment_method == "xendit":
        # Generate mock Xendit token
        payment_token = f"xendit-invoice-{uuid.uuid4().hex[:16]}"
        redirect_url = f"https://checkout.xendit.co/{payment_token}"
    elif payload.payment_method == "manual_transfer":
        # Manual transfer doesn't need token
        redirect_url = None
    
    transaction = VoteTransaction(
        user_id=current_user.id,
        package_id=payload.package_id,
        event_id=payload.event_id,
        points_amount=package.points_amount,
        amount_idr=package.price_idr,
        status="PENDING",
        payment_provider=payload.payment_method,
        payment_token=payment_token,
        redirect_url=redirect_url,
        idempotency_key=idem_key,
        expires_at=expires_at
    )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    return VotePurchaseResponse(
        transaction_id=transaction.id,
        package_id=transaction.package_id,
        points_amount=transaction.points_amount,
        amount_idr=transaction.amount_idr,
        status=transaction.status,
        payment_provider=transaction.payment_provider,
        payment_token=transaction.payment_token,
        redirect_url=transaction.redirect_url,
        expires_at=transaction.expires_at,
        created_at=transaction.created_at
    )


# ---------------------------------------------------------------------------
# Check Purchase Status
# ---------------------------------------------------------------------------

from app.schemas.voting import VotePurchaseStatusResponse


@router.get(
    "/purchase/{transaction_id}/status",
    response_model=VotePurchaseStatusResponse,
    summary="Check purchase status",
    tags=["Voting"],
)
def check_purchase_status(
    transaction_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Check status of a vote purchase transaction.
    
    **Auth:** Required (user can only check their own transactions)
    """
    transaction = db.query(VoteTransaction).filter(
        VoteTransaction.id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Verify user owns this transaction
    if transaction.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this transaction")
    
    # Check if expired
    retry_available = False
    if transaction.status == "PENDING" and transaction.expires_at:
        if transaction.expires_at < datetime.utcnow():
            transaction.status = "EXPIRED"
            db.commit()
        else:
            retry_available = True
    
    return VotePurchaseStatusResponse(
        transaction_id=transaction.id,
        status=transaction.status,
        package_id=transaction.package_id,
        points_amount=transaction.points_amount,
        amount_idr=transaction.amount_idr,
        paid_at=transaction.paid_at,
        payment_method=transaction.payment_provider,
        failure_reason=transaction.failure_reason,
        retry_available=retry_available
    )
