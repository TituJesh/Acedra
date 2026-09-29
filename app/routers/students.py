from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_admin
from app.models.student import Student
from app.models.department import Department
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.student import (
    StudentCreate,
    StudentUpdate,
    StudentResponse
)
from app.utils.logger import logger


router = APIRouter(
    prefix="/students",
    tags=["Students"]
)


@router.post(
    "/",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED
)
def create_student(
    student_data: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    user = (
        db.query(User)
        .filter(User.id == student_data.user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must have student role"
        )

    existing_user_student = (
        db.query(Student)
        .filter(Student.user_id == student_data.user_id)
        .first()
    )

    if existing_user_student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a student profile"
        )

    existing_student = (
        db.query(Student)
        .filter(Student.student_id == student_data.student_id)
        .first()
    )

    if existing_student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student ID already exists"
        )

    existing_email = (
        db.query(Student)
        .filter(Student.email == student_data.email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student email already exists"
        )

    department = (
        db.query(Department)
        .filter(Department.id == student_data.department_id)
        .first()
    )

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    new_student = Student(
        user_id=student_data.user_id,
        student_id=student_data.student_id,
        first_name=student_data.first_name,
        last_name=student_data.last_name,
        email=student_data.email,
        phone=student_data.phone,
        date_of_birth=student_data.date_of_birth,
        gender=student_data.gender,
        department_id=student_data.department_id,
        year=student_data.year,
        address=student_data.address
    )

    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    logger.info(f"Student created: student_id={new_student.student_id}")

    return new_student


@router.get(
    "/",
    response_model=list[StudentResponse]
)
def get_students(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    department_id: int | None = Query(None, description="Filter by department ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Student)
    if department_id is not None:
        query = query.filter(Student.department_id == department_id)

    students = query.offset(skip).limit(limit).all()

    return students


@router.get(
    "/me",
    response_model=StudentResponse
)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    student = (
        db.query(Student)
        .filter(Student.user_id == current_user.id)
        .first()
    )

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )

    return student


@router.get(
    "/search",
    response_model=list[StudentResponse]
)
def search_students(
    query: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    search_query = f"%{query}%"

    students = (
        db.query(Student)
        .filter(
            (Student.student_id.ilike(search_query))
            | (Student.first_name.ilike(search_query))
            | (Student.last_name.ilike(search_query))
            | (Student.email.ilike(search_query))
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    return students


@router.get(
    "/{student_id}",
    response_model=StudentResponse
)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    if current_user.role != "admin" and student.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: cannot view other student profiles"
        )

    return student


@router.put(
    "/{student_id}",
    response_model=StudentResponse
)
def update_student(
    student_id: int,
    student_data: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    update_data = student_data.model_dump(
        exclude_unset=True
    )

    if "department_id" in update_data:
        department = (
            db.query(Department)
            .filter(
                Department.id == update_data["department_id"]
            )
            .first()
        )

        if department is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found"
            )

    if "email" in update_data:
        existing_email = (
            db.query(Student)
            .filter(
                Student.email == update_data["email"],
                Student.id != student_id
            )
            .first()
        )

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student email already exists"
            )

    for field, value in update_data.items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)

    logger.info(f"Student updated: student_id={student.student_id}")

    return student


@router.delete(
    "/{student_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK
)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    db.delete(student)
    db.commit()

    logger.info(f"Student deleted: student_id={student.student_id}")

    return {
        "message": "Student deleted successfully"
    }