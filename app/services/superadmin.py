import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import security
from app.models.event import (
    AssessmentGroup,
    AssessmentItem,
    AssessmentSection,
    Event,
    EventCategory,
    Team,
    TeamMember,
)
from app.models.scoring import ScoreItem, ScoreSheet
from app.models.transaction import (
    Transaction,
    VoteCandidate,
    VoteCategory,
    VotePackage,
)
from app.models.user import EventUser, User
from app.schemas.events import (
    CategoryCreate,
    CategoryUpdate,
    EventCreate,
    EventSchemaUpload,
    EventStaffCreate,
    EventUpdate,
)
from app.schemas.registration import (
    MemberCreate,
    TeamLotUpdate,
    TeamStatusUpdate,
)
from app.schemas.scoring import CategoryRankingRead, TeamRankEntry
from app.schemas.transaction import DashboardStats, EventStats, TransactionVerify
from app.schemas.user import UserAdminCreate, UserUpdate
from app.schemas.voting import (
    VoteCandidateCreate,
    VoteCandidateUpdate,
    VoteCategoryCreate,
    VoteCategoryUpdate,
    VotePackageCreate,
    VotePackageUpdate,
)

# ===========================================================================
# USER MANAGEMENT
# ===========================================================================


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
):
    """List all users with optional filters."""
    query = db.query(User).filter(User.deleted_at.is_(None))

    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        query = query.filter(
            User.full_name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%")
        )

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "skip": skip, "limit": limit, "data": users}


def get_user(db: Session, user_id: uuid.UUID):
    """Get a single user by ID."""
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return user


def create_user_by_admin(db: Session, payload: UserAdminCreate):
    """SuperAdmin creates a user with an explicit role."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email sudah digunakan",
        )

    new_user = User(
        id=uuid.uuid4(),
        email=payload.email,
        full_name=payload.full_name,
        password_hash=security.get_password_hash(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def update_user(db: Session, user_id: uuid.UUID, payload: UserUpdate):
    """Update user fields (role, active status, name, points)."""
    user = get_user(db, user_id)

    update_data = payload.model_dump(exclude_unset=True)

    if "role" in update_data and update_data["role"] not in ("SUPER_ADMIN", "USER"):
        raise HTTPException(
            status_code=400,
            detail="Role tidak valid. Pilihan: SUPER_ADMIN, USER",
        )

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: uuid.UUID):
    """Soft-delete a user (set deleted_at timestamp)."""
    user = get_user(db, user_id)

    if user.role == "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Akun SuperAdmin tidak dapat dihapus",
        )

    user.deleted_at = func.now()
    user.is_active = False
    db.commit()
    return {"message": "User berhasil dihapus", "user_id": user_id}


# ===========================================================================
# EVENT MANAGEMENT
# ===========================================================================


def get_all_events_admin(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
):
    """List all events (including inactive) for admin view."""
    query = db.query(Event)

    if is_active is not None:
        query = query.filter(Event.is_active == is_active)
    if search:
        query = query.filter(
            Event.title.ilike(f"%{search}%") | Event.slug.ilike(f"%{search}%")
        )

    total = query.count()
    events = query.order_by(Event.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "skip": skip, "limit": limit, "data": events}


def get_event_admin(db: Session, event_id: uuid.UUID):
    """Get full event detail including categories."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")
    return event


def create_event_admin(db: Session, payload: EventCreate):
    """Create a new event (SuperAdmin only)."""
    if db.query(Event).filter(Event.slug == payload.slug).first():
        raise HTTPException(status_code=400, detail="Slug sudah digunakan")

    new_event = Event(**payload.model_dump())
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event


def update_event(db: Session, event_id: uuid.UUID, payload: EventUpdate):
    """Full update of an event by SuperAdmin."""
    event = get_event_admin(db, event_id)

    update_data = payload.model_dump(exclude_unset=True)

    # Prevent slug collision
    if "slug" in update_data:
        existing = (
            db.query(Event)
            .filter(Event.slug == update_data["slug"], Event.id != event_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400, detail="Slug sudah digunakan event lain"
            )

    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event_id: uuid.UUID):
    """Soft-delete an event by setting is_active=False."""
    event = get_event_admin(db, event_id)
    event.is_active = False
    db.commit()
    return {"message": "Event berhasil dinonaktifkan", "event_id": event_id}


def toggle_event_pg(db: Session, event_id: uuid.UUID):
    """Toggle the Payment Gateway feature for an event."""
    event = get_event_admin(db, event_id)
    event.is_pg_enabled = not event.is_pg_enabled
    db.commit()
    db.refresh(event)
    return {
        "message": "Payment Gateway diperbarui",
        "event_id": event_id,
        "is_pg_enabled": event.is_pg_enabled,
    }


def toggle_event_voting(db: Session, event_id: uuid.UUID):
    """Toggle the Voting feature for an event."""
    event = get_event_admin(db, event_id)
    event.is_voting_enabled = not event.is_voting_enabled
    db.commit()
    db.refresh(event)
    return {
        "message": "Fitur Voting diperbarui",
        "event_id": event_id,
        "is_voting_enabled": event.is_voting_enabled,
    }


def toggle_event_active(db: Session, event_id: uuid.UUID):
    """Toggle the active/published status of an event."""
    event = get_event_admin(db, event_id)
    event.is_active = not event.is_active
    db.commit()
    db.refresh(event)
    return {
        "message": "Status event diperbarui",
        "event_id": event_id,
        "is_active": event.is_active,
    }


# ===========================================================================
# EVENT STAFF MANAGEMENT
# ===========================================================================


def get_event_staff(db: Session, event_id: uuid.UUID):
    """List all assigned staff members for an event."""
    _assert_event_exists(db, event_id)
    staff = db.query(EventUser).filter(EventUser.event_id == event_id).all()
    return staff


def assign_event_staff(db: Session, event_id: uuid.UUID, payload: EventStaffCreate):
    """Assign a user a role on a specific event."""
    _assert_event_exists(db, event_id)

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    valid_roles = ["ORGANIZER", "JUDGE", "TABULATOR", "OFFICIAL_TEAM"]
    if payload.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Role tidak valid. Pilihan: {valid_roles}",
        )

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
            status_code=400,
            detail="User sudah memiliki role tersebut di event ini",
        )

    assignment = EventUser(
        id=uuid.uuid4(),
        event_id=event_id,
        user_id=payload.user_id,
        role=payload.role,
        meta_data=payload.meta_data,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def remove_event_staff(db: Session, event_user_id: uuid.UUID):
    """Remove a staff assignment from an event."""
    assignment = db.query(EventUser).filter(EventUser.id == event_user_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment tidak ditemukan")
    db.delete(assignment)
    db.commit()
    return {
        "message": "Staff berhasil dihapus dari event",
        "event_user_id": event_user_id,
    }


# ===========================================================================
# CATEGORY MANAGEMENT
# ===========================================================================


def get_categories(db: Session, event_id: uuid.UUID):
    """List all categories for an event."""
    _assert_event_exists(db, event_id)
    return db.query(EventCategory).filter(EventCategory.event_id == event_id).all()


def create_category(db: Session, event_id: uuid.UUID, payload: CategoryCreate):
    """Create a new category for an event."""
    _assert_event_exists(db, event_id)

    new_cat = EventCategory(
        id=uuid.uuid4(),
        event_id=event_id,
        name=payload.name,
        max_quota=payload.max_quota,
        registration_fee=payload.registration_fee,
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat


def update_category(db: Session, category_id: uuid.UUID, payload: CategoryUpdate):
    """Update a category's name, quota, or fee."""
    cat = _get_category_or_404(db, category_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cat, field, value)

    db.commit()
    db.refresh(cat)
    return cat


def delete_category(db: Session, category_id: uuid.UUID):
    """Delete a category (cascades to assessment sections, groups, items)."""
    cat = _get_category_or_404(db, category_id)

    # Guard: do not delete if registered teams exist
    registered = (
        db.query(func.count(Team.id))
        .filter(
            Team.category_id == category_id,
            Team.status.in_(["REGISTERED", "PENDING_PAYMENT", "PENDING_VERIFICATION"]),
        )
        .scalar()
    )
    if registered > 0:
        raise HTTPException(
            status_code=400,
            detail="Kategori tidak dapat dihapus karena masih ada tim terdaftar",
        )

    db.delete(cat)
    db.commit()
    return {"message": "Kategori berhasil dihapus", "category_id": category_id}


# ===========================================================================
# ASSESSMENT SCHEMA MANAGEMENT
# ===========================================================================


def upload_assessment_schema(db: Session, payload: EventSchemaUpload):
    """
    Upload a full hierarchical assessment schema (Sections > Groups > Items).
    Replaces any existing schema for the given category.
    """
    _get_category_or_404(db, payload.category_id)  # validates existence

    # Delete existing schema for this category
    existing_sections = (
        db.query(AssessmentSection)
        .filter(AssessmentSection.category_id == payload.category_id)
        .all()
    )
    for section in existing_sections:
        groups = (
            db.query(AssessmentGroup)
            .filter(AssessmentGroup.section_id == section.id)
            .all()
        )
        for group in groups:
            db.query(AssessmentItem).filter(
                AssessmentItem.group_id == group.id
            ).delete()
            db.delete(group)
        db.delete(section)

    db.flush()

    # Insert new schema
    for s_idx, section_data in enumerate(payload.sections):
        new_section = AssessmentSection(
            id=uuid.uuid4(),
            category_id=payload.category_id,
            title=section_data.title,
            weight_percentage=section_data.weight_percentage,
            sort_order=section_data.sort_order
            if section_data.sort_order is not None
            else s_idx,
        )
        db.add(new_section)
        db.flush()

        for g_idx, group_data in enumerate(section_data.groups):
            new_group = AssessmentGroup(
                id=uuid.uuid4(),
                section_id=new_section.id,
                title=group_data.title,
                sort_order=group_data.sort_order
                if group_data.sort_order is not None
                else g_idx,
            )
            db.add(new_group)
            db.flush()

            for item_data in group_data.items:
                new_item = AssessmentItem(
                    id=uuid.uuid4(),
                    group_id=new_group.id,
                    label=item_data.label,
                    display_number=item_data.display_number,
                    allowed_values=item_data.allowed_values,
                )
                db.add(new_item)

    db.commit()
    return {
        "message": "Schema penilaian berhasil diunggah",
        "category_id": payload.category_id,
        "sections_count": len(payload.sections),
    }


def get_assessment_schema(db: Session, category_id: uuid.UUID):
    """Retrieve the full nested assessment schema for a category."""
    _get_category_or_404(db, category_id)  # validates existence

    sections = (
        db.query(AssessmentSection)
        .filter(AssessmentSection.category_id == category_id)
        .order_by(AssessmentSection.sort_order)
        .all()
    )

    result = []
    for section in sections:
        groups = (
            db.query(AssessmentGroup)
            .filter(AssessmentGroup.section_id == section.id)
            .order_by(AssessmentGroup.sort_order)
            .all()
        )
        groups_data = []
        for group in groups:
            items = (
                db.query(AssessmentItem)
                .filter(AssessmentItem.group_id == group.id)
                .order_by(AssessmentItem.display_number)
                .all()
            )
            groups_data.append(
                {
                    "id": group.id,
                    "title": group.title,
                    "sort_order": group.sort_order,
                    "items": [
                        {
                            "id": i.id,
                            "label": i.label,
                            "display_number": i.display_number,
                            "allowed_values": i.allowed_values,
                        }
                        for i in items
                    ],
                }
            )
        result.append(
            {
                "id": section.id,
                "title": section.title,
                "weight_percentage": section.weight_percentage,
                "sort_order": section.sort_order,
                "groups": groups_data,
            }
        )

    return {"category_id": category_id, "sections": result}


# ===========================================================================
# TEAM MANAGEMENT
# ===========================================================================


def get_teams_by_event(
    db: Session,
    event_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    category_id: Optional[uuid.UUID] = None,
):
    """List all teams for an event with optional filters."""
    _assert_event_exists(db, event_id)

    query = db.query(Team).filter(Team.event_id == event_id)
    if status:
        query = query.filter(Team.status == status)
    if category_id:
        query = query.filter(Team.category_id == category_id)

    total = query.count()
    teams = query.order_by(Team.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "skip": skip, "limit": limit, "data": teams}


def get_team_detail(db: Session, team_id: uuid.UUID):
    """Get full team info including members."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")
    return team


def update_team_status(db: Session, team_id: uuid.UUID, payload: TeamStatusUpdate):
    """Update team status (admin action)."""
    valid_statuses = [
        "PENDING_PAYMENT",
        "PENDING_VERIFICATION",
        "REGISTERED",
        "CANCELLED",
        "DISQUALIFIED",
    ]
    if payload.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Status tidak valid. Pilihan: {valid_statuses}",
        )

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    team.status = payload.status
    db.commit()
    db.refresh(team)
    return {
        "message": "Status tim diperbarui",
        "team_id": team_id,
        "new_status": team.status,
    }


def update_team_lot(db: Session, team_id: uuid.UUID, payload: TeamLotUpdate):
    """Assign or update a team's lot number."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    # Check uniqueness within the same category
    conflict = (
        db.query(Team)
        .filter(
            Team.category_id == team.category_id,
            Team.lot_number == payload.lot_number,
            Team.id != team_id,
        )
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=400,
            detail=f"Nomor lot {payload.lot_number} sudah digunakan oleh tim lain di kategori ini",
        )

    team.lot_number = payload.lot_number
    db.commit()
    db.refresh(team)
    return {
        "message": "Nomor lot berhasil diatur",
        "team_id": team_id,
        "lot_number": team.lot_number,
    }


def delete_team(db: Session, team_id: uuid.UUID):
    """Delete a team and all related members."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    db.delete(team)
    db.commit()
    return {"message": "Tim berhasil dihapus", "team_id": team_id}


def get_team_members(db: Session, team_id: uuid.UUID):
    """Get all members of a team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")
    return db.query(TeamMember).filter(TeamMember.team_id == team_id).all()


def add_team_member_admin(db: Session, team_id: uuid.UUID, payload: MemberCreate):
    """Admin adds a member to any team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    new_member = TeamMember(
        id=uuid.uuid4(),
        team_id=team_id,
        name=payload.name,
        role=payload.role,
        identity_number=payload.identity_number,
        extra_data=payload.extra_data,
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member


def update_team_member(db: Session, member_id: uuid.UUID, payload):
    """Update a team member's details."""
    member = db.query(TeamMember).filter(TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Anggota tidak ditemukan")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, field, value)

    db.commit()
    db.refresh(member)
    return member


def delete_team_member(db: Session, member_id: uuid.UUID):
    """Remove a member from a team."""
    member = db.query(TeamMember).filter(TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Anggota tidak ditemukan")

    db.delete(member)
    db.commit()
    return {"message": "Anggota berhasil dihapus", "member_id": member_id}


# ===========================================================================
# TRANSACTION MANAGEMENT
# ===========================================================================


def get_all_transactions(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    transaction_type: Optional[str] = None,
):
    """List all transactions across the platform."""
    query = db.query(Transaction)

    if status:
        query = query.filter(Transaction.status == status)
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)

    total = query.count()
    transactions = (
        query.order_by(Transaction.created_at.desc()).offset(skip).limit(limit).all()
    )
    return {"total": total, "skip": skip, "limit": limit, "data": transactions}


def get_event_transactions(
    db: Session,
    event_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
):
    """List all REGISTRATION transactions for an event by checking metadata."""
    _assert_event_exists(db, event_id)

    # Transactions are linked to teams via metadata.event_id
    query = db.query(Transaction).filter(
        Transaction.transaction_type == "REGISTRATION",
        Transaction.meta_data["event_id"].astext == str(event_id),
    )
    if status:
        query = query.filter(Transaction.status == status)

    total = query.count()
    transactions = (
        query.order_by(Transaction.created_at.desc()).offset(skip).limit(limit).all()
    )
    return {"total": total, "skip": skip, "limit": limit, "data": transactions}


def verify_transaction(
    db: Session, transaction_id: uuid.UUID, payload: TransactionVerify
):
    """Approve or reject a REGISTRATION payment transaction."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

    if tx.status not in ("PENDING", "PENDING_VERIFICATION"):
        raise HTTPException(
            status_code=400,
            detail=f"Transaksi tidak dapat diverifikasi (status saat ini: {tx.status})",
        )

    team_id = tx.meta_data.get("team_id") if tx.meta_data else None
    team = db.query(Team).filter(Team.id == team_id).first() if team_id else None

    if payload.is_approved:
        tx.status = "PAID"
        tx.paid_at = func.now()
        if team:
            team.status = "REGISTERED"
    else:
        if not payload.admin_note:
            raise HTTPException(
                status_code=400,
                detail="admin_note wajib diisi saat menolak transaksi",
            )
        tx.status = "FAILED"
        tx.meta_data = {**(tx.meta_data or {}), "admin_note": payload.admin_note}
        if team:
            team.status = "CANCELLED"

    db.commit()
    return {
        "message": "Verifikasi berhasil diproses",
        "transaction_id": transaction_id,
        "new_status": tx.status,
        "team_id": team_id,
    }


# ===========================================================================
# VOTE PACKAGE MANAGEMENT
# ===========================================================================


def get_vote_packages(db: Session):
    """List all vote packages."""
    return db.query(VotePackage).order_by(VotePackage.price_idr).all()


def create_vote_package(db: Session, payload: VotePackageCreate):
    """Create a new vote package."""
    package = VotePackage(
        id=uuid.uuid4(),
        name=payload.name,
        price_idr=payload.price_idr,
        points_amount=payload.points_amount,
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


def update_vote_package(db: Session, package_id: uuid.UUID, payload: VotePackageUpdate):
    """Update a vote package."""
    package = db.query(VotePackage).filter(VotePackage.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Paket voting tidak ditemukan")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(package, field, value)

    db.commit()
    db.refresh(package)
    return package


def delete_vote_package(db: Session, package_id: uuid.UUID):
    """Delete a vote package."""
    package = db.query(VotePackage).filter(VotePackage.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Paket voting tidak ditemukan")

    db.delete(package)
    db.commit()
    return {"message": "Paket voting berhasil dihapus", "package_id": package_id}


# ===========================================================================
# VOTE CATEGORY MANAGEMENT
# ===========================================================================


def get_vote_categories(db: Session, event_id: uuid.UUID):
    """List all vote categories for an event."""
    _assert_event_exists(db, event_id)
    return db.query(VoteCategory).filter(VoteCategory.event_id == event_id).all()


def create_vote_category(db: Session, event_id: uuid.UUID, payload: VoteCategoryCreate):
    """Create a new voting category for an event."""
    _assert_event_exists(db, event_id)

    new_cat = VoteCategory(
        id=uuid.uuid4(),
        event_id=event_id,
        name=payload.name,
        description=payload.description,
        target_event_category_id=payload.target_event_category_id,
        is_active=payload.is_active,
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return new_cat


def update_vote_category(
    db: Session, vote_category_id: uuid.UUID, payload: VoteCategoryUpdate
):
    """Update a voting category."""
    cat = db.query(VoteCategory).filter(VoteCategory.id == vote_category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Kategori voting tidak ditemukan")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cat, field, value)

    db.commit()
    db.refresh(cat)
    return cat


def delete_vote_category(db: Session, vote_category_id: uuid.UUID):
    """Delete a voting category and its candidates."""
    cat = db.query(VoteCategory).filter(VoteCategory.id == vote_category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Kategori voting tidak ditemukan")

    db.delete(cat)
    db.commit()
    return {
        "message": "Kategori voting berhasil dihapus",
        "vote_category_id": vote_category_id,
    }


# ===========================================================================
# VOTE CANDIDATE MANAGEMENT
# ===========================================================================


def get_vote_candidates(db: Session, vote_category_id: uuid.UUID):
    """List candidates for a vote category."""
    cat = db.query(VoteCategory).filter(VoteCategory.id == vote_category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Kategori voting tidak ditemukan")
    return (
        db.query(VoteCandidate)
        .filter(VoteCandidate.vote_category_id == vote_category_id)
        .all()
    )


def add_vote_candidate(
    db: Session, vote_category_id: uuid.UUID, payload: VoteCandidateCreate
):
    """Add a candidate to a voting category."""
    cat = db.query(VoteCategory).filter(VoteCategory.id == vote_category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Kategori voting tidak ditemukan")

    team = db.query(Team).filter(Team.id == payload.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    # Prevent duplicate candidate in same category
    existing = (
        db.query(VoteCandidate)
        .filter(
            VoteCandidate.vote_category_id == vote_category_id,
            VoteCandidate.team_id == payload.team_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Tim ini sudah terdaftar sebagai kandidat di kategori voting ini",
        )

    candidate = VoteCandidate(
        id=uuid.uuid4(),
        vote_category_id=vote_category_id,
        team_id=payload.team_id,
        candidate_name=payload.candidate_name or team.name,
        image_url=payload.image_url,
        total_votes=0,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def update_vote_candidate(
    db: Session, candidate_id: uuid.UUID, payload: VoteCandidateUpdate
):
    """Update a vote candidate's display info."""
    candidate = db.query(VoteCandidate).filter(VoteCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Kandidat tidak ditemukan")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(candidate, field, value)

    db.commit()
    db.refresh(candidate)
    return candidate


def delete_vote_candidate(db: Session, candidate_id: uuid.UUID):
    """Remove a candidate from a voting category."""
    candidate = db.query(VoteCandidate).filter(VoteCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Kandidat tidak ditemukan")

    db.delete(candidate)
    db.commit()
    return {"message": "Kandidat berhasil dihapus", "candidate_id": candidate_id}


# ===========================================================================
# SCORE SHEET MANAGEMENT
# ===========================================================================


def get_score_sheets(
    db: Session,
    event_id: uuid.UUID,
    category_id: Optional[uuid.UUID] = None,
):
    """
    List all score sheets for an event.
    Optionally filter by category (joins via Team → EventCategory).
    """
    _assert_event_exists(db, event_id)

    query = (
        db.query(ScoreSheet)
        .join(Team, Team.id == ScoreSheet.team_id)
        .filter(Team.event_id == event_id)
    )

    if category_id:
        query = query.filter(Team.category_id == category_id)

    return query.order_by(ScoreSheet.created_at.desc()).all()


def get_team_scores(db: Session, team_id: uuid.UUID):
    """Get all score sheets for a specific team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    sheets = db.query(ScoreSheet).filter(ScoreSheet.team_id == team_id).all()

    result = []
    for sheet in sheets:
        items = db.query(ScoreItem).filter(ScoreItem.sheet_id == sheet.id).all()
        result.append(
            {
                "id": sheet.id,
                "team_id": sheet.team_id,
                "judge_id": sheet.judge_id,
                "inputter_id": sheet.inputter_id,
                "total_score": sheet.total_score,
                "is_locked": sheet.is_locked,
                "created_at": sheet.created_at,
                "updated_at": sheet.updated_at,
                "items": [
                    {
                        "id": item.id,
                        "sheet_id": item.sheet_id,
                        "assessment_item_id": item.assessment_item_id,
                        "value": item.value,
                        "created_at": item.created_at,
                        "updated_at": item.updated_at,
                    }
                    for item in items
                ],
            }
        )
    return result


def lock_score_sheet(db: Session, sheet_id: uuid.UUID):
    """Lock a score sheet so it cannot be modified further."""
    sheet = db.query(ScoreSheet).filter(ScoreSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Score sheet tidak ditemukan")

    if sheet.is_locked:
        raise HTTPException(status_code=400, detail="Score sheet sudah dikunci")

    sheet.is_locked = True
    db.commit()
    db.refresh(sheet)
    return {
        "sheet_id": sheet.id,
        "is_locked": sheet.is_locked,
        "message": "Score sheet berhasil dikunci",
    }


def unlock_score_sheet(db: Session, sheet_id: uuid.UUID):
    """Unlock a previously locked score sheet (SuperAdmin override)."""
    sheet = db.query(ScoreSheet).filter(ScoreSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Score sheet tidak ditemukan")

    sheet.is_locked = False
    db.commit()
    db.refresh(sheet)
    return {
        "sheet_id": sheet.id,
        "is_locked": sheet.is_locked,
        "message": "Score sheet berhasil dibuka kembali",
    }


def get_category_rankings(db: Session, event_id: uuid.UUID, category_id: uuid.UUID):
    """
    Compute rankings for a category.
    Score = average of all judges' total_score per team.
    Only considers locked sheets to ensure finality.
    """
    _assert_event_exists(db, event_id)
    cat = _get_category_or_404(db, category_id)

    teams = (
        db.query(Team)
        .filter(Team.event_id == event_id, Team.category_id == category_id)
        .all()
    )

    ranking_data = []
    for team in teams:
        sheets = (
            db.query(ScoreSheet)
            .filter(ScoreSheet.team_id == team.id, ScoreSheet.is_locked.is_(True))
            .all()
        )
        if not sheets:
            avg_score = 0.0
            judge_count = 0
        else:
            avg_score = sum(s.total_score for s in sheets) / len(sheets)
            judge_count = len(sheets)

        ranking_data.append(
            {
                "team_id": team.id,
                "team_name": team.name,
                "lot_number": team.lot_number,
                "total_score": round(avg_score, 4),
                "judge_count": judge_count,
            }
        )

    # Sort by total_score descending, then lot_number ascending as tiebreaker
    ranking_data.sort(key=lambda x: (-x["total_score"], x["lot_number"] or 9999))

    ranked = []
    for i, entry in enumerate(ranking_data):
        ranked.append(
            TeamRankEntry(
                rank=i + 1,
                team_id=entry["team_id"],
                team_name=entry["team_name"],
                lot_number=entry["lot_number"],
                total_score=entry["total_score"],
                judge_count=entry["judge_count"],
            )
        )

    return CategoryRankingRead(
        event_id=event_id,
        category_id=category_id,
        category_name=cat.name,
        rankings=ranked,
    )


# ===========================================================================
# DASHBOARD & STATISTICS
# ===========================================================================


def get_dashboard_stats(db: Session) -> DashboardStats:
    """Compute platform-wide statistics for the SuperAdmin dashboard."""

    total_users = (
        db.query(func.count(User.id)).filter(User.deleted_at.is_(None)).scalar()
    )
    total_active_users = (
        db.query(func.count(User.id))
        .filter(User.deleted_at.is_(None), User.is_active.is_(True))
        .scalar()
    )
    total_events = db.query(func.count(Event.id)).scalar()
    total_active_events = (
        db.query(func.count(Event.id)).filter(Event.is_active.is_(True)).scalar()
    )
    total_teams = db.query(func.count(Team.id)).scalar()
    total_registered_teams = (
        db.query(func.count(Team.id)).filter(Team.status == "REGISTERED").scalar()
    )

    total_revenue_raw = (
        db.query(func.sum(Transaction.amount))
        .filter(Transaction.status == "PAID")
        .scalar()
    )
    total_revenue_idr = float(total_revenue_raw or 0)

    total_pending_transactions = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.status.in_(["PENDING", "PENDING_VERIFICATION"]))
        .scalar()
    )

    total_vote_packages_sold = (
        db.query(func.count(Transaction.id))
        .filter(
            Transaction.transaction_type == "VOTE_PURCHASE",
            Transaction.status == "PAID",
        )
        .scalar()
    )

    events = db.query(Event).all()
    event_stats = []
    for event in events:
        total_t = (
            db.query(func.count(Team.id)).filter(Team.event_id == event.id).scalar()
        )
        registered_t = (
            db.query(func.count(Team.id))
            .filter(Team.event_id == event.id, Team.status == "REGISTERED")
            .scalar()
        )
        pending_pay_t = (
            db.query(func.count(Team.id))
            .filter(Team.event_id == event.id, Team.status == "PENDING_PAYMENT")
            .scalar()
        )
        pending_ver_t = (
            db.query(func.count(Team.id))
            .filter(Team.event_id == event.id, Team.status == "PENDING_VERIFICATION")
            .scalar()
        )
        cancelled_t = (
            db.query(func.count(Team.id))
            .filter(Team.event_id == event.id, Team.status == "CANCELLED")
            .scalar()
        )
        revenue_raw = (
            db.query(func.sum(Transaction.amount))
            .filter(
                Transaction.status == "PAID",
                Transaction.meta_data["event_id"].astext == str(event.id),
            )
            .scalar()
        )
        event_stats.append(
            EventStats(
                event_id=event.id,
                event_title=event.title,
                slug=event.slug,
                total_teams=total_t,
                registered_teams=registered_t,
                pending_payment_teams=pending_pay_t,
                pending_verification_teams=pending_ver_t,
                cancelled_teams=cancelled_t,
                total_revenue_idr=float(revenue_raw or 0),
                is_active=event.is_active,
            )
        )

    return DashboardStats(
        total_users=total_users,
        total_active_users=total_active_users,
        total_events=total_events,
        total_active_events=total_active_events,
        total_teams=total_teams,
        total_registered_teams=total_registered_teams,
        total_revenue_idr=total_revenue_idr,
        total_pending_transactions=total_pending_transactions,
        total_vote_packages_sold=total_vote_packages_sold,
        events=event_stats,
    )


# ===========================================================================
# PRIVATE HELPERS
# ===========================================================================


def _assert_event_exists(db: Session, event_id: uuid.UUID) -> None:
    """Raise 404 if the event does not exist."""
    if not db.query(Event).filter(Event.id == event_id).first():
        raise HTTPException(status_code=404, detail="Event tidak ditemukan")


def _get_category_or_404(db: Session, category_id: uuid.UUID) -> EventCategory:
    """Return the EventCategory or raise 404."""
    cat = db.query(EventCategory).filter(EventCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Kategori tidak ditemukan")
    return cat
