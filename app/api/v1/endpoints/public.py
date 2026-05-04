from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.public import EventPreview, LandingPageResponse
from app.services.public import PublicService
from app.models.event import Event

router = APIRouter()


@router.get(
    "/events",
    response_model=List[EventPreview],
    summary="List all active events (catalogue)",
    tags=["Public"],
)

def get_all_events_preview(db: Session = Depends(deps.get_db)):
    """
    Returns a lightweight list of all **active** events for the public catalogue.

    Each entry contains only the fields needed to render an event card:
    title, slug, organizer, dates, banner URL, and registration / voting status.

    No authentication required.
    """
    return PublicService.get_all_events_preview(db)


@router.get(
    "/event/{slug}",
    response_model=LandingPageResponse,
    summary="Get event landing page data",
    tags=["Public"],
)
def get_landing_data(slug: str, db: Session = Depends(deps.get_db)):
    """
    Returns the **complete payload** needed to render an event's public landing page.

    Sections included:
    - **event** — title, dates, theme settings, content blocks
    - **registration** — open/closed status, per-category slot availability
    - **voting** — current phase (DISABLED / PREPARATION / LIVE / CLOSED),
      vote categories, and candidate listings

    No authentication required.
    """
    data = PublicService.get_event_landing_page(db, slug)
    if not data:
        raise HTTPException(
            status_code=404,
            detail="Event tidak ditemukan atau tidak aktif",
        )
    return data


# ---------------------------------------------------------------------------
# Public Voting Endpoints
# ---------------------------------------------------------------------------

from datetime import datetime
from uuid import UUID
from fastapi import Query
from sqlalchemy import func
from app.models.transaction import VoteCategory, VoteCandidate, Vote
from app.schemas.voting import (
    PublicVoteCategoriesResponse,
    PublicVoteCategoryRead,
    PublicVoteCandidatesResponse,
    PublicVoteCandidateRead,
)


@router.get(
    "/events/{event_id}/vote-categories",
    response_model=PublicVoteCategoriesResponse,
    summary="Get public vote categories for an event",
    tags=["Public Voting"],
)
def get_public_vote_categories(
    event_id: UUID,
    db: Session = Depends(deps.get_db),
):
    """
    Get all active vote categories for an event (public access).
    Includes candidate count and total votes cast.
    """
    from app.models.event import Event
    
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get active vote categories with stats
    categories = db.query(VoteCategory).filter(
        VoteCategory.event_id == event_id,
        VoteCategory.is_active == True
    ).all()
    
    result_categories = []
    for category in categories:
        # Count candidates
        candidate_count = db.query(VoteCandidate).filter(
            VoteCandidate.vote_category_id == category.id
        ).count()
        
        # Sum total votes
        total_votes = db.query(func.sum(VoteCandidate.total_votes)).filter(
            VoteCandidate.vote_category_id == category.id
        ).scalar() or 0
        
        result_categories.append(PublicVoteCategoryRead(
            id=category.id,
            name=category.name,
            description=category.description,
            target_event_category_id=category.target_event_category_id,
            is_active=category.is_active,
            candidate_count=candidate_count,
            total_votes_cast=total_votes
        ))
    
    return PublicVoteCategoriesResponse(
        event_id=event_id,
        categories=result_categories
    )


@router.get(
    "/vote-categories/{category_id}/candidates",
    response_model=PublicVoteCandidatesResponse,
    summary="Get public vote candidates with rankings",
    tags=["Public Voting"],
)
def get_public_vote_candidates(
    category_id: UUID,
    db: Session = Depends(deps.get_db),
):
    """
    Get all candidates for a vote category with rankings (public access).
    """
    # Get category with event info
    category = db.query(VoteCategory).filter(VoteCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Vote category not found")
    
    # Get candidates ordered by total_votes DESC, then display_order
    candidates = db.query(VoteCandidate).filter(
        VoteCandidate.vote_category_id == category_id
    ).order_by(
        VoteCandidate.total_votes.desc(),
        VoteCandidate.display_order.asc()
    ).all()
    
    # Calculate rankings
    result_candidates = []
    current_rank = 0
    previous_votes = None
    
    for i, candidate in enumerate(candidates):
        # Handle ties - same votes = same rank
        if candidate.total_votes != previous_votes:
            current_rank = i + 1
            previous_votes = candidate.total_votes
        
        result_candidates.append(PublicVoteCandidateRead(
            id=candidate.id,
            team_id=candidate.team_id,
            candidate_name=candidate.candidate_name or "Unknown",
            image_url=candidate.image_url,
            display_order=candidate.display_order,
            total_votes=candidate.total_votes,
            rank=current_rank,
            last_vote_at=candidate.last_vote_at
        ))
    
    # Calculate total votes in category
    total_votes_in_category = sum(c.total_votes for c in candidates)
    
    return PublicVoteCandidatesResponse(
        category_id=category_id,
        event_id=category.event_id,
        candidates=result_candidates,
        total_votes_in_category=total_votes_in_category,
        last_updated=datetime.utcnow()
    )


# ---------------------------------------------------------------------------
# Real-time Vote Stream (SSE)
# ---------------------------------------------------------------------------

from fastapi.responses import StreamingResponse
import asyncio
import json


@router.get(
    "/events/{event_id}/vote-stream",
    summary="Real-time vote stream (SSE)",
    tags=["Public"],
)
async def vote_stream(
    event_id: UUID,
    request: Request,
    db: Session = Depends(deps.get_db),
):
    """
    Server-Sent Events endpoint for real-time vote updates.
    
    **Auth:** Optional
    **Protocol:** Server-Sent Events (SSE)
    
    Events:
    - `vote_update`: Individual candidate vote count update
    - `leaderboard_update`: Top 3 rankings update per category
    - `heartbeat`: Keep-alive every 30 seconds
    
    **Security:**
    - Max 1 connection per IP per event
    - Auto-disconnect after 5 minutes (client should reconnect)
    """
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if voting is enabled for this event
    if not event.is_voting_enabled:
        raise HTTPException(status_code=403, detail="Voting is not enabled for this event")
    
    async def event_generator():
        """Generate SSE events"""
        start_time = datetime.utcnow()
        last_heartbeat = start_time
        
        # Cache for last known state (to avoid duplicate events)
        last_vote_counts = {}
        last_leaderboards = {}
        
        while True:
            try:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                # Auto-disconnect after 5 minutes
                if (datetime.utcnow() - start_time).total_seconds() > 300:
                    yield f"event: disconnect\ndata: {{\"reason\": \"timeout\"}}\n\n"
                    break
                
                # Send heartbeat every 30 seconds
                if (datetime.utcnow() - last_heartbeat).total_seconds() >= 30:
                    yield f"event: heartbeat\ndata: {{\"timestamp\": \"{datetime.utcnow().isoformat()}\"}}\n\n"
                    last_heartbeat = datetime.utcnow()
                
                # Check for vote updates (query every 2 seconds)
                # In production, this should use Redis pub/sub
                candidates = db.query(VoteCandidate).join(
                    VoteCategory, VoteCandidate.vote_category_id == VoteCategory.id
                ).filter(
                    VoteCategory.event_id == event_id
                ).all()
                
                for candidate in candidates:
                    last_count = last_vote_counts.get(str(candidate.id), 0)
                    if candidate.total_votes != last_count:
                        # Vote count changed
                        vote_update = {
                            "candidate_id": str(candidate.id),
                            "new_total": candidate.total_votes,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        yield f"event: vote_update\ndata: {json.dumps(vote_update)}\n\n"
                        last_vote_counts[str(candidate.id)] = candidate.total_votes
                
                # Check for leaderboard updates per category
                categories = db.query(VoteCategory).filter(
                    VoteCategory.event_id == event_id,
                    VoteCategory.is_active == True
                ).all()
                
                for category in categories:
                    # Get top 3 candidates for this category
                    top_candidates = db.query(VoteCandidate).filter(
                        VoteCandidate.vote_category_id == category.id
                    ).order_by(VoteCandidate.total_votes.desc()).limit(3).all()
                    
                    leaderboard_data = [
                        {
                            "id": str(c.id),
                            "team_id": str(c.team_id),
                            "candidate_name": c.candidate_name,
                            "image_url": c.image_url,
                            "display_order": c.display_order,
                            "total_votes": c.total_votes,
                            "rank": idx + 1,
                            "last_vote_at": c.last_vote_at.isoformat() if c.last_vote_at else None
                        }
                        for idx, c in enumerate(top_candidates)
                    ]
                    
                    # Check if leaderboard changed
                    last_leaderboard = last_leaderboards.get(str(category.id), [])
                    if leaderboard_data != last_leaderboard:
                        leaderboard_update = {
                            "category_id": str(category.id),
                            "top_3": leaderboard_data,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        yield f"event: leaderboard_update\ndata: {json.dumps(leaderboard_update)}\n\n"
                        last_leaderboards[str(category.id)] = leaderboard_data
                
                # Wait before next check
                await asyncio.sleep(2)
                
            except Exception as e:
                # Log error but keep connection alive
                yield f"event: error\ndata: {{\"message\": \"{str(e)}\"}}\n\n"
                await asyncio.sleep(5)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
