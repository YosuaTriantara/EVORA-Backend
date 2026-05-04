from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.scoring import ScoreSheet
from app.models.event import Team, EventCategory


# ---------------------------------------------------------------------------
# Scoring Sheet Lock/Unlock (Event-Scoped for TABULATOR)
# ---------------------------------------------------------------------------


def lock_score_sheet(db: Session, sheet_id: UUID):
    """Lock a score sheet (event-scoped for TABULATOR)."""
    sheet = db.query(ScoreSheet).filter(ScoreSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Score sheet not found")

    sheet.is_locked = True
    db.commit()
    db.refresh(sheet)
    return {
        "sheet_id": sheet_id,
        "is_locked": True,
        "message": "Score sheet berhasil dikunci"
    }


def unlock_score_sheet(db: Session, sheet_id: UUID):
    """Unlock a score sheet (event-scoped for TABULATOR)."""
    sheet = db.query(ScoreSheet).filter(ScoreSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Score sheet not found")

    sheet.is_locked = False
    db.commit()
    db.refresh(sheet)
    return {
        "sheet_id": sheet_id,
        "is_locked": False,
        "message": "Score sheet berhasil dibuka kembali"
    }


# ---------------------------------------------------------------------------
# Rankings (Event-Scoped for ORGANIZER, JUDGE, TABULATOR)
# ---------------------------------------------------------------------------


def get_rankings(db: Session, event_id: UUID, category_id: UUID):
    """Get rankings for a category (event-scoped)."""
    # Verify category belongs to event
    category = db.query(EventCategory).filter(
        EventCategory.id == category_id,
        EventCategory.event_id == event_id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found in this event")

    # Get all teams in this category with their scores
    teams = (
        db.query(Team)
        .options(joinedload(Team.score_sheets))
        .filter(Team.category_id == category_id)
        .all()
    )

    # Calculate rankings
    rankings = []
    for team in teams:
        # Get all score sheets for this team
        score_sheets = [s for s in team.score_sheets if s.is_locked]
        
        if score_sheets:
            total_score = sum(s.total_score for s in score_sheets)
            judge_count = len(score_sheets)
            avg_score = total_score / judge_count if judge_count > 0 else 0
        else:
            total_score = 0
            judge_count = 0
            avg_score = 0

        rankings.append({
            "team_id": team.id,
            "team_name": team.name,
            "lot_number": team.lot_number,
            "total_score": avg_score,
            "judge_count": judge_count,
            "raw_total": total_score,
        })

    # Sort by total_score descending
    rankings.sort(key=lambda x: x["total_score"], reverse=True)

    # Assign ranks (handle ties)
    result = []
    current_rank = 1
    prev_score = None
    
    for i, r in enumerate(rankings):
        if prev_score is not None and r["total_score"] < prev_score:
            current_rank = i + 1
        
        result.append({
            "rank": current_rank,
            "team_id": r["team_id"],
            "team_name": r["team_name"],
            "lot_number": r["lot_number"],
            "total_score": r["total_score"],
            "judge_count": r["judge_count"],
        })
        prev_score = r["total_score"]

    return {
        "event_id": event_id,
        "category_id": category_id,
        "category_name": category.name,
        "rankings": result,
    }


# ---------------------------------------------------------------------------
# Assessment Schema (Event-Scoped for JUDGE, TABULATOR)
# ---------------------------------------------------------------------------


def get_assessment_schema(db: Session, category_id: UUID):
    """Get assessment schema for a category (event-scoped)."""
    from app.models.scoring import AssessmentSection, AssessmentGroup, AssessmentItem
    
    # Get all sections for this category
    sections = db.query(AssessmentSection).filter(
        AssessmentSection.category_id == category_id
    ).order_by(AssessmentSection.sort_order).all()
    
    if not sections:
        raise HTTPException(status_code=404, detail="Assessment schema not found for this category")
    
    # Build the schema response
    sections_data = []
    for section in sections:
        # Get groups for this section
        groups = db.query(AssessmentGroup).filter(
            AssessmentGroup.section_id == section.id
        ).order_by(AssessmentGroup.sort_order).all()
        
        groups_data = []
        for group in groups:
            # Get items for this group
            items = db.query(AssessmentItem).filter(
                AssessmentItem.group_id == group.id
            ).order_by(AssessmentItem.display_number).all()
            
            items_data = []
            for item in items:
                items_data.append({
                    "id": item.id,
                    "label": item.label,
                    "display_number": item.display_number,
                    "allowed_values": item.allowed_values,
                })
            
            groups_data.append({
                "id": group.id,
                "title": group.title,
                "sort_order": group.sort_order,
                "items": items_data,
            })
        
        sections_data.append({
            "id": section.id,
            "title": section.title,
            "weight_percentage": section.weight_percentage,
            "sort_order": section.sort_order,
            "groups": groups_data,
        })
    
    return {
        "category_id": category_id,
        "sections": sections_data,
    }
