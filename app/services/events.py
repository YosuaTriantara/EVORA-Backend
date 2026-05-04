from asyncio import events
from datetime import date, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import flag_modified

from app.config.settings import DEFAULT_TIMEZONE
from app.models import event
from app.models.event import Event, EventCategory
from app.models.user import EventUser, User
from app.schemas.events import CategoryCreate, EventCreate, EventRead, EventReadFull, EventUpdateCustom, EventStaffCreate
from app.utils.helpers import deep_merge, get_current_time


def get_event_stage(event: Event):
    now = get_current_time().date()

    if event.event_date_start and now < event.event_date_start:
        return "registration"

    if event.event_date_start and event.event_date_end and event.event_date_start <= now <= event.event_date_end:
        return "competition"

    if event.event_date_end and now > event.event_date_end:
        return "post-competition"

    return "upcoming"


def get_events(db: Session, skip: int = 0, limit: int = 10):
    events = db.query(Event).offset(skip).limit(limit).all()

    result = []
    for event in events:
        event_schema = EventRead.model_validate(event)

        event_with_stage = event_schema.model_copy(
            update={"stage": get_event_stage(event)}
        )

        result.append(event_with_stage)

    return result


def get_event_by_slug(db: Session, slug: str):
    try:
        event_id = UUID(slug)
        event = db.query(Event).filter((Event.slug == slug) | (Event.id == event_id)).first()
    except ValueError:
        event = db.query(Event).filter(Event.slug == slug).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event_schema = EventRead.model_validate(event)

    return event_schema.model_copy(update={"stage": get_event_stage(event)})


def get_event_by_id(db: Session, event_id: UUID):
    """Get full event details by ID including categories."""
    event = (
        db.query(Event)
        .options(joinedload(Event.categories))
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event_schema = EventReadFull.model_validate(event)

    return event_schema.model_copy(update={"stage": get_event_stage(event)})


def create_event(db: Session, payload: EventCreate):
    if db.query(Event).filter(Event.slug == payload.slug).first():
        raise HTTPException(status_code=400, detail="Slug already exists!")

    new_event = Event(**payload.model_dump())
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event


def create_category(db: Session, event_id: UUID, payload: CategoryCreate):
    if payload.event_id != event_id:
        raise HTTPException(status_code=400, detail="Invalid Event ID format")

    new_cat = EventCategory(**payload.model_dump())
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat


def get_user_managed_events(db: Session, user_id: UUID):
    """
    Mengambil semua event aktif di mana user memiliki assignment peran tertentu.
    Menggunakan joinedload untuk mencegah N+1 query problem.
    Mendukung skenario multi-event dan multi-peran (satu user bisa menjadi
    ORGANIZER di event A, JUDGE di event B, TABULATOR di event C, dst.)
    karena setiap baris EventUser adalah assignment independen.
    """
    event_assignments = (
        db.query(EventUser)
        .join(Event, EventUser.event_id == Event.id)
        .options(joinedload(EventUser.event))
        .filter(EventUser.user_id == user_id, Event.is_active == True)
        .all()
    )

    result = []
    for assignment in event_assignments:
        ev = assignment.event
        result.append(
            {
                "role": assignment.role,
                "meta_data": assignment.meta_data,
                "event": {
                    "id": ev.id,
                    "title": ev.title,
                    "slug": ev.slug,
                    "organizer": ev.organizer,
                    "profil_url": ev.profil_url,
                    "event_date_start": ev.event_date_start,
                    "event_date_end": ev.event_date_end,
                    "banner_url": ev.profil_url,
                    "is_registration_open": ev.is_active,
                    "is_voting_live": ev.is_voting_enabled,
                    "location": ev.location,
                },
            }
        )
    return result


def update_event_customization(db: Session, event_id: UUID, payload: EventUpdateCustom):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")

    update_data = payload.model_dump(exclude_unset=True)

    # Validasi Payment Gateway hanya jika content_data dikirim
    if "content_data" in update_data:
        payment_methods = (
            update_data["content_data"].get("payment_config", {}).get("methods", [])
        )

        if "PAYMENT_GATEWAY" in payment_methods and not event.is_pg_enabled:
            raise HTTPException(
                status_code=403,
                detail="Fitur Payment Gateway belum diaktifkan untuk event ini.",
            )

        event.content_data = deep_merge(
            update_data["content_data"], event.content_data or {}
        )
        flag_modified(event, "content_data")

    if "theme_settings" in update_data:
        event.theme_settings = deep_merge(
            update_data["theme_settings"], event.theme_settings or {}
        )
        flag_modified(event, "theme_settings")

    if "is_voting_live" in update_data:
        event.is_voting_live = update_data["is_voting_live"]

    db.commit()
    db.refresh(event)
    return event


# ---------------------------------------------------------------------------
# Event Staff Management (Event-Scoped)
# ---------------------------------------------------------------------------


def get_event_staff(db: Session, event_id: UUID):
    """Get all staff members for an event with user details."""
    staff = (
        db.query(EventUser)
        .options(joinedload(EventUser.user))
        .filter(EventUser.event_id == event_id)
        .all()
    )
    return staff


def add_event_staff(db: Session, event_id: UUID, payload: EventStaffCreate):
    """Add a staff member to an event."""
    # Check if user exists
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user already has this role in this event
    existing = (
        db.query(EventUser)
        .filter(
            EventUser.event_id == event_id,
            EventUser.user_id == payload.user_id,
            EventUser.role == payload.role,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="User already has this role in this event"
        )

    # Create new event user assignment
    new_staff = EventUser(
        event_id=event_id,
        user_id=payload.user_id,
        role=payload.role,
        meta_data=payload.meta_data,
    )
    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)
    return new_staff


def remove_event_staff(db: Session, event_id: UUID, event_user_id: UUID):
    """Remove a staff member from an event."""
    staff = (
        db.query(EventUser)
        .filter(EventUser.id == event_user_id, EventUser.event_id == event_id)
        .first()
    )
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    db.delete(staff)
    db.commit()
    return {"message": "Staff berhasil dihapus dari event", "event_user_id": event_user_id}


def update_category(db: Session, category_id: UUID, payload):
    """Update event category (event-scoped)."""
    category = db.query(EventCategory).filter(EventCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: UUID):
    """Delete event category (event-scoped)."""
    category = db.query(EventCategory).filter(EventCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if category has active/registered teams
    from app.models.event import Team
    active_teams = (
        db.query(Team)
        .filter(
            Team.category_id == category_id,
            Team.status.in_(["REGISTERED", "PENDING_PAYMENT", "PENDING_VERIFICATION"]),
        )
        .count()
    )
    if active_teams > 0:
        raise HTTPException(
            status_code=400,
            detail="Category has active/registered teams (deletion blocked)",
        )

    db.delete(category)
    db.commit()
    return {"message": "Category berhasil dihapus", "category_id": category_id}
