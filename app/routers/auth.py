from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.dependencies import get_current_user, require_admin

from app.database import SessionLocal
from app.schemas.auth import UserRegister, UserLogin, TokenResponse
from app.utils.security import hash_password, verify_password
from app.utils.jwt import create_access_token
from app.models.user import User
from app.utils.logger import logger

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post("/register")
def register(
    user: UserRegister,
    db: Session = Depends(get_db)
):
    hashed_password = hash_password(user.password)

    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        role=user.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"User registered: user_id={new_user.id}, username={new_user.username}")

    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "role": new_user.role
    }

@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    existing_user = (
        db.query(User)
        .filter(User.username == form_data.username)
        .first()
    )

    if existing_user is None:
        logger.warning(f"Failed login attempt: username '{form_data.username}' not found")
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    password_is_correct = verify_password(
        form_data.password,
        existing_user.password_hash
    )

    if not password_is_correct:
        logger.warning(f"Failed login attempt: incorrect password for user_id={existing_user.id}")
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    access_token = create_access_token(
        {
            "user_id": existing_user.id,
            "role": existing_user.role
        }
    )

    logger.info(f"User logged in successfully: user_id={existing_user.id}, username={existing_user.username}")

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role
    }

@router.get("/admin-test")
def admin_test(
    current_user: User = Depends(require_admin)
):
    return {
        "message": "Welcome Admin",
        "username": current_user.username,
        "role": current_user.role
    }