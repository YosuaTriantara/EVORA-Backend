from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api import deps
from app.models.user import User
from app.schemas.user import UserCreate, Token, UserRead
from app.services import auth as service

router = APIRouter(tags=["Auth"])

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    db: Session = Depends(deps.get_db)
):
    """
    Mendaftarkan user baru ke dalam sistem.
    """
    return service.register_user(db=db, payload=payload)

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(deps.get_db)
):
    """
    Login user untuk mendapatkan Access Token (JWT).
    """
    return service.authenticate_user(
        db=db, 
        email=form_data.username, 
        password=form_data.password
    )

@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(deps.get_current_user)):
    """
    Mengambil informasi profil user yang sedang login.
    """
    return current_user