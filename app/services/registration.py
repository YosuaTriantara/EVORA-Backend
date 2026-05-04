import uuid
from typing import Optional
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api import deps
from app.models.event import Team, EventCategory, TeamMember
from app.models.user import EventUser
from app.models.transaction import Transaction
from app.schemas.registration import TeamCreate, MemberCreate, MemberUpdate, TeamStatusUpdate, TeamLotUpdate

def register_team(payload: TeamCreate,
                  db: Session,
                  current_user:EventUser ):

    try:
        # 1. ATOMIC LOCK & QUOTA CHECK
        category = db.query(EventCategory).filter(EventCategory.id == payload.category_id).with_for_update().first()
        if not category:
            raise HTTPException(status_code=404, detail="Kategori tidak ditemukan")

        occupied_slots = db.query(func.count(Team.id)).filter(
            Team.category_id == payload.category_id,
            Team.status.in_(["REGISTERED", "PENDING_PAYMENT", "PENDING_VERIFICATION"])
        ).scalar()

        if occupied_slots >= category.max_quota:
            raise HTTPException(status_code=400, detail="Kuota kategori sudah penuh")

        # 2. CREATE TEAM ENTITY
        new_team = Team(
            id=uuid.uuid4(),
            event_id=payload.event_id,
            category_id=payload.category_id,
            official_user_id=current_user.id,
            name=payload.team_name,
            institution=payload.institution,
            status="PENDING_PAYMENT"
        )
        db.add(new_team)

        # 3. ROLE ASSIGNMENT
        existing_access = db.query(EventUser).filter(
            EventUser.event_id == payload.event_id,
            EventUser.user_id == current_user.id
        ).first()

        if not existing_access:
            db.add(EventUser(event_id=payload.event_id, user_id=current_user.id, role="OFFICIAL_TEAM"))

        db.commit()
        db.refresh(new_team)
        return {"message": "Pendaftaran berhasil, slot diamankan", "team_id": new_team.id}

    except Exception as e:
        db.rollback()
        raise e
    
async def upload_payment_proof(team_id: uuid.UUID,
                               file: UploadFile,
                               db: Session,
                               current_user=EventUser):

    team = db.query(Team).filter(Team.id == team_id, Team.official_user_id == current_user.id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    # Simpan file bukti pembayaran (logika penyimpanan file diabaikan untuk kesederhanaan)
    file_location = f"payment_proofs/{team_id}_{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(await file.read())

    # Perbarui status tim
    team.status = "PENDING_VERIFICATION"
    db.commit()
    return {"message": "Bukti pembayaran berhasil diunggah dan menunggu verifikasi."}

def get_my_teams(event_id: Optional[uuid.UUID],
                 db: Session,
                 current_user:EventUser):

    query = db.query(Team).filter(Team.official_user_id == current_user.id)
    if event_id is not None:
        query = query.filter(Team.event_id == event_id)

    return query.all()
 
def verify_registration_payment(transaction_id: uuid.UUID,
                                is_approved: bool,
                                admin_note: str,
                                db: Session,
                                current_user: EventUser):
    
    tx = db.query(Transaction).filter(Transaction.id == transaction_id, 
                                      Transaction.transaction_type == "REGISTRATION").first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

    team_id = tx.meta_data.get("team_id")
    team = db.query(Team).filter(Team.id == team_id).first()

    if is_approved:
        tx.status = "PAID"
        tx.paid_at = func.now()
        if team:
            team.status = "REGISTERED"
            # Di sini Anda bisa assign nomor urut (lot_number) jika diperlukan
    else:
        tx.status = "FAILED"
        tx.meta_data = {**tx.meta_data, "admin_note": admin_note}
        if team:
            team.status = "CANCELLED" # Kuota dilepaskan kembali

    db.commit()
    return {"message": "Verifikasi berhasil diproses", "new_status": tx.status}


def update_team(team_id: uuid.UUID,
                         new_team_name: str,
                         new_institution: str,
                         db: Session,
                         current_user: EventUser):
    
    # Pastikan yang update adalah pemilik tim (Official)
    team = db.query(Team).filter(Team.id == team_id, 
                                 Team.official_user_id == current_user.id).first()

    if not team:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses ke tim ini")

    # Batasi apa yang bisa diubah oleh Official
    if new_team_name:
        team.name = new_team_name
    if new_institution:
        team.institution = new_institution

    db.commit()
    db.refresh(team)
    return {"message": "Profil tim berhasil diperbarui", "team": team}

def get_team_members(team_id: uuid.UUID,
                    db: Session,
                    current_user: EventUser):
    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    return members

def add_team_member(team_id: uuid.UUID,
                    member: MemberCreate,
                    db: Session,
                    current_user: EventUser):

    team = db.query(Team).filter(Team.id == team_id, Team.official_user_id == current_user.id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Tim tidak ditemukan")

    new_member = TeamMember(
        id=uuid.uuid4(),
        team_id=team_id,
        name=member.name,
        identity_number=member.identity_number,
        role=member.role,
        extra_data=member.extra_data
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member


# ---------------------------------------------------------------------------
# Team Status & Lot Management (Event-Scoped for ORGANIZER)
# ---------------------------------------------------------------------------


def update_team_status(db: Session, team_id: uuid.UUID, payload: TeamStatusUpdate):
    """Update team status (event-scoped for ORGANIZER)."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    old_status = team.status
    new_status = payload.status

    # Validate status
    valid_statuses = ["PENDING_PAYMENT", "PENDING_VERIFICATION", "REGISTERED", "CANCELLED", "DISQUALIFIED"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    team.status = new_status

    # Side effects: Update transaction based on status change
    if new_status == "REGISTERED":
        # Create or update transaction to PAID
        tx = db.query(Transaction).filter(
            Transaction.meta_data.contains({"team_id": str(team_id)}),
            Transaction.transaction_type == "REGISTRATION"
        ).first()
        if tx:
            tx.status = "PAID"
            tx.paid_at = func.now()
        else:
            # Create new transaction if not exists
            new_tx = Transaction(
                id=uuid.uuid4(),
                user_id=team.official_user_id,
                transaction_type="REGISTRATION",
                amount=0,  # Manual registration
                status="PAID",
                paid_at=func.now(),
                meta_data={"team_id": str(team_id), "manual_status_update": True}
            )
            db.add(new_tx)
    elif new_status in ["CANCELLED", "DISQUALIFIED"]:
        # Update transaction to FAILED
        tx = db.query(Transaction).filter(
            Transaction.meta_data.contains({"team_id": str(team_id)}),
            Transaction.transaction_type == "REGISTRATION"
        ).first()
        if tx:
            tx.status = "FAILED"

    db.commit()
    db.refresh(team)
    return {"message": "Status tim diperbarui", "team_id": team_id, "new_status": new_status}


def update_team_lot(db: Session, team_id: uuid.UUID, payload: TeamLotUpdate):
    """Update team lot number (event-scoped for ORGANIZER)."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    lot_number = payload.lot_number

    # Validate lot_number >= 1
    if lot_number < 1:
        raise HTTPException(status_code=400, detail="Lot number must be >= 1")

    # Check if lot number is unique within the same category
    existing = db.query(Team).filter(
        Team.category_id == team.category_id,
        Team.lot_number == lot_number,
        Team.id != team_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Lot number already taken in this category")

    team.lot_number = lot_number
    db.commit()
    db.refresh(team)
    return {"message": "Nomor lot berhasil diatur", "team_id": team_id, "lot_number": lot_number}


# ---------------------------------------------------------------------------
# Team Member Management (Event-Scoped for OFFICIAL_TEAM)
# ---------------------------------------------------------------------------


def update_team_member(
    member_id: uuid.UUID,
    payload: MemberUpdate,
    db: Session,
    current_user: EventUser
):
    """Update a team member's details (event-scoped for OFFICIAL_TEAM)."""
    # Get the member and verify team ownership
    member = db.query(TeamMember).filter(TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Anggota tim tidak ditemukan")
    
    # Verify the current user is the official user of the team
    team = db.query(Team).filter(
        Team.id == member.team_id,
        Team.official_user_id == current_user.id
    ).first()
    if not team:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses untuk mengubah anggota tim ini")
    
    # Update fields
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(member, field, value)
    
    db.commit()
    db.refresh(member)
    return member


def delete_team_member(
    member_id: uuid.UUID,
    db: Session,
    current_user: EventUser
):
    """Remove a member from a team (event-scoped for OFFICIAL_TEAM)."""
    # Get the member and verify team ownership
    member = db.query(TeamMember).filter(TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Anggota tim tidak ditemukan")
    
    # Verify the current user is the official user of the team
    team = db.query(Team).filter(
        Team.id == member.team_id,
        Team.official_user_id == current_user.id
    ).first()
    if not team:
        raise HTTPException(status_code=403, detail="Anda tidak memiliki akses untuk menghapus anggota tim ini")
    
    db.delete(member)
    db.commit()
    return {"message": "Anggota tim berhasil dihapus", "member_id": member_id}
