from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from pydantic import ValidationError
from uuid import UUID
from app.db.session import SessionLocal
from app.models.user import User, EventUser
from app.models.event import EventCategory, Team
from app.models.scoring import ScoreSheet
from app.models.transaction import Transaction, VoteCandidate, VoteCategory
from app.schemas.token import TokenPayload
import os

# Link login untuk Swagger UI
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db), 
    token: str = Depends(reusable_oauth2)
) -> User:
    """
    Validasi Token JWT dan pastikan User-nya ada di database.
    """
    try:
        payload = jwt.decode(
            token, os.getenv("SECRET_KEY"), algorithms=["HS256"]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    user = db.query(User).filter(User.id == token_data.sub).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user

# --- ROLE-BASED ACCESS CONTROL (RBAC) ---
def get_super_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Akses ini hanya untuk Admin")
    return current_user

# 2. Satpam Event: Cek role spesifik di event tertentu
class EventRoleChecker:
    def __init__(self, allowed_roles: list):
        """
        allowed_roles: List role yang diizinkan, 
        misal: ["ORGANIZER", "TABULATOR"]
        """
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        event_id: Optional[UUID] = None,
        vote_category_id: Optional[UUID] = None,
        candidate_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
        sheet_id: Optional[UUID] = None,
        transaction_id: Optional[UUID] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        # 1. BYPASS: Super Admin selalu punya akses ke semua pintu
        if current_user.role == "SUPER_ADMIN":
            return current_user

        if not event_id:
            if vote_category_id:
                category = (
                    db.query(VoteCategory)
                    .filter(VoteCategory.id == vote_category_id)
                    .first()
                )
                if category:
                    event_id = category.event_id
            elif candidate_id:
                candidate = (
                    db.query(VoteCandidate)
                    .filter(VoteCandidate.id == candidate_id)
                    .first()
                )
                if candidate:
                    category = (
                        db.query(VoteCategory)
                        .filter(VoteCategory.id == candidate.vote_category_id)
                        .first()
                    )
                    if category:
                        event_id = category.event_id
            elif category_id:
                category = (
                    db.query(EventCategory)
                    .filter(EventCategory.id == category_id)
                    .first()
                )
                if category:
                    event_id = category.event_id
            elif team_id:
                team = db.query(Team).filter(Team.id == team_id).first()
                if team:
                    event_id = team.event_id
            elif sheet_id:
                sheet = db.query(ScoreSheet).filter(ScoreSheet.id == sheet_id).first()
                if sheet:
                    team = db.query(Team).filter(Team.id == sheet.team_id).first()
                    if team:
                        event_id = team.event_id
            elif transaction_id:
                tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
                if tx and tx.meta_data:
                    raw_event_id = tx.meta_data.get("event_id")
                    raw_team_id = tx.meta_data.get("team_id")
                    if raw_event_id:
                        try:
                            event_id = UUID(str(raw_event_id))
                        except (TypeError, ValueError):
                            event_id = raw_event_id
                    elif raw_team_id:
                        try:
                            raw_team_id = UUID(str(raw_team_id))
                        except (TypeError, ValueError):
                            pass
                        team = db.query(Team).filter(Team.id == raw_team_id).first()
                        if team:
                            event_id = team.event_id

        if not event_id:
            access = (
                db.query(EventUser)
                .filter(
                    EventUser.user_id == current_user.id,
                    EventUser.role.in_(self.allowed_roles),
                )
                .first()
            )
            if access:
                return current_user
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event ID is required for role validation"
            )

        # 2. VALIDASI: Cek tiket user di tabel event_users
        access = db.query(EventUser).filter(
            EventUser.event_id == event_id,
            EventUser.user_id == current_user.id,
            EventUser.role.in_(self.allowed_roles)
        ).first()

        if not access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Akses ditolak. Anda tidak memiliki akses sebagai {self.allowed_roles} di event ini."
            )
        
        return current_user
