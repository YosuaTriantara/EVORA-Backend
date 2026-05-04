from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.services import users as service

router = APIRouter()


@router.get(
    "/search",
    summary="Search users",
    tags=["Users"],
)
def search_users(
    q: str = Query(..., description="Search query (email or full_name)"),
    limit: int = Query(10, ge=1, le=20, description="Max results (default: 10, max: 20)"),
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.EventRoleChecker(["ORGANIZER"])),
):
    """
    Search users by email or full_name.
    
    **Auth:** Required
    **Permission:** ORGANIZER (limited search only, cannot list all users)
    
    **Query Parameters:**
    - `q`: Search query (email or full_name) - required
    - `limit`: Max results (default: 10, max: 20)
    
    **Returns:**
    - Limited fields: id, email, full_name only
    - Only users with role USER (not SUPER_ADMIN)
    - Use for finding users to add as staff
    """
    return service.search_users(db, query=q, limit=limit)


# ---------------------------------------------------------------------------
# User Vote Balance & History
# ---------------------------------------------------------------------------

from app.schemas.voting import UserVoteBalanceRead, VoteHistoryResponse


@router.get(
    "/me/vote-balance",
    response_model=UserVoteBalanceRead,
    summary="Get user vote balance for an event",
    tags=["Users"],
)
def get_user_vote_balance(
    event_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Get user's vote point balance for a specific event.
    
    **Auth:** Required
    **Cache:** No cache (real-time balance)
    """
    from app.models.transaction import UserVoteBalance
    
    balance = db.query(UserVoteBalance).filter(
        UserVoteBalance.user_id == current_user.id,
        UserVoteBalance.event_id == event_id
    ).first()
    
    if not balance:
        # Return zero balance if no record exists
        return UserVoteBalanceRead(
            user_id=current_user.id,
            event_id=event_id,
            point_balance=0,
            total_points_purchased=0,
            total_points_spent=0,
            last_purchase_at=None,
            expires_at=None
        )
    
    return UserVoteBalanceRead(
        user_id=balance.user_id,
        event_id=balance.event_id,
        point_balance=balance.point_balance,
        total_points_purchased=balance.total_purchased,
        total_points_spent=balance.total_spent,
        last_purchase_at=balance.last_purchase_at,
        expires_at=None  # Not implemented yet
    )


@router.get(
    "/me/vote-history",
    response_model=VoteHistoryResponse,
    summary="Get user vote history",
    tags=["Users"],
)
def get_user_vote_history(
    event_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Get user's voting history for a specific event.
    
    **Auth:** Required
    **Pagination:** Required (max limit 100)
    """
    from app.models.transaction import Vote, VoteCandidate, VoteCategory
    from app.schemas.voting import VoteHistoryItem
    from sqlalchemy import func
    
    # Get total count
    total = db.query(func.count(Vote.id)).filter(
        Vote.user_id == current_user.id,
        Vote.event_id == event_id
    ).scalar()
    
    # Get paginated votes with candidate and category info
    votes = db.query(Vote).filter(
        Vote.user_id == current_user.id,
        Vote.event_id == event_id
    ).order_by(
        Vote.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    # Build response with candidate and category names
    data = []
    for vote in votes:
        candidate = db.query(VoteCandidate).filter(
            VoteCandidate.id == vote.candidate_id
        ).first()
        
        category = None
        if candidate:
            category = db.query(VoteCategory).filter(
                VoteCategory.id == candidate.vote_category_id
            ).first()
        
        data.append(VoteHistoryItem(
            id=vote.id,
            candidate_id=vote.candidate_id,
            candidate_name=candidate.candidate_name if candidate else "Unknown",
            category_name=category.name if category else "Unknown",
            points=vote.points,
            created_at=vote.created_at,
            event_id=vote.event_id
        ))
    
    return VoteHistoryResponse(
        total=total,
        skip=skip,
        limit=limit,
        data=data
    )
