import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core import security
from app.models.user import User
from app.schemas.user import UserCreate

def register_user(db: Session, payload: UserCreate):
    # 1. Cek apakah user sudah ada
    user_exists = db.query(User).filter(User.email == payload.email).first()
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email sudah digunakan"
        )
    
    # 2. Buat entitas user baru
    new_user = User(
        id=uuid.uuid4(),
        email=payload.email,
        full_name=payload.full_name,
        password_hash=security.get_password_hash(payload.password),
        role="USER"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def authenticate_user(db: Session, email: str, password: str):
    # 1. Cari user berdasarkan email
    user = db.query(User).filter(User.email == email).first()
    
    # 2. Verifikasi keberadaan user dan password
    if not user or not security.verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Email atau password salah"
        )
    
    # 3. Buat token akses
    access_token = security.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}