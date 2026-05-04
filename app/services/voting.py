from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.transaction import VoteCategory, VoteCandidate
from app.schemas.voting import VoteCategoryCreate, VoteCategoryUpdate, VoteCandidateCreate, VoteCandidateUpdate


# ---------------------------------------------------------------------------
# Vote Category Management (Event-Scoped)
# ---------------------------------------------------------------------------


def get_vote_categories(db: Session, event_id: UUID):
    """Get all vote categories for an event."""
    categories = db.query(VoteCategory).filter(VoteCategory.event_id == event_id).all()
    return categories


def create_vote_category(db: Session, event_id: UUID, payload: VoteCategoryCreate):
    """Create a new vote category for an event."""
    new_category = VoteCategory(
        event_id=event_id,
        name=payload.name,
        description=payload.description,
        target_event_category_id=payload.target_event_category_id,
        is_active=payload.is_active,
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


def update_vote_category(db: Session, vote_category_id: UUID, payload: VoteCategoryUpdate):
    """Update a vote category."""
    category = db.query(VoteCategory).filter(VoteCategory.id == vote_category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Vote category not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


def delete_vote_category(db: Session, vote_category_id: UUID):
    """Delete a vote category."""
    category = db.query(VoteCategory).filter(VoteCategory.id == vote_category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Vote category not found")

    db.delete(category)
    db.commit()
    return {"message": "Kategori voting berhasil dihapus", "vote_category_id": vote_category_id}


# ---------------------------------------------------------------------------
# Vote Candidate Management (Event-Scoped)
# ---------------------------------------------------------------------------


def get_vote_candidates(db: Session, vote_category_id: UUID):
    """Get all vote candidates for a category."""
    candidates = db.query(VoteCandidate).filter(VoteCandidate.vote_category_id == vote_category_id).all()
    return candidates


def create_vote_candidate(db: Session, event_id: UUID, payload: VoteCandidateCreate):
    """Create a new vote candidate."""
    # Verify that the vote category belongs to the event
    category = db.query(VoteCategory).filter(
        VoteCategory.id == payload.vote_category_id,
        VoteCategory.event_id == event_id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Vote category not found in this event")

    new_candidate = VoteCandidate(
        vote_category_id=payload.vote_category_id,
        team_id=payload.team_id,
        candidate_name=payload.candidate_name,
        image_url=payload.image_url,
    )
    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)
    return new_candidate


def update_vote_candidate(db: Session, candidate_id: UUID, payload: VoteCandidateUpdate):
    """Update a vote candidate."""
    candidate = db.query(VoteCandidate).filter(VoteCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Vote candidate not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(candidate, field, value)

    db.commit()
    db.refresh(candidate)
    return candidate


def delete_vote_candidate(db: Session, candidate_id: UUID):
    """Delete a vote candidate."""
    candidate = db.query(VoteCandidate).filter(VoteCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Vote candidate not found")

    db.delete(candidate)
    db.commit()
    return {"message": "Kandidat voting berhasil dihapus", "candidate_id": candidate_id}
