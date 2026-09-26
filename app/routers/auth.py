from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_admin
from app.schemas.auth import (
    TokenResponse,
    UserRegister,
    UserRegisterResponse,
    UserResponse,
)
from app.utils.security import hash_password, verify_password
from app.utils.jwt import create_access_token
from app.models.user import User
from app.utils.logger import logger


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED
)
def register(
    user: UserRegister,
    db: Session = Depends(get_db)
):
    existing_username = (
        db.query(User)
        .filter(User.username == user.username)
        .first()
    )

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    existing_email = (
        db.query(User)
        .filter(User.email == user.email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    if user.role not in ["admin", "student"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be either 'admin' or 'student'"
        )

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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    password_is_correct = verify_password(
        form_data.password,
        existing_user.password_hash
    )

    if not password_is_correct:
        logger.warning(f"Failed login attempt: incorrect password for user_id={existing_user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
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


@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.get("/admin-test")
def admin_test(
    current_user: User = Depends(require_admin)
):
    return {
        "message": "Welcome Admin",
        "username": current_user.username,
        "role": current_user.role
    }