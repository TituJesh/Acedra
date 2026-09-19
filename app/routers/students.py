from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.student import Student
from app.models.department import Department
from app.models.user import User
from app.schemas.student import (
    StudentCreate,
    StudentUpdate,
    StudentResponse
)
from app.dependencies import get_current_user, require_admin
from app.utils.logger import logger


router = APIRouter(
    prefix="/students",
    tags=["Students"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/",
    response_model=StudentResponse,
    status_code=201
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
            status_code=404,
            detail="User not found"
        )

    if user.role != "student":
        raise HTTPException(
            status_code=400,
            detail="User must have student role"
        )

    existing_user_student = (
        db.query(Student)
        .filter(Student.user_id == student_data.user_id)
        .first()
    )

    if existing_user_student:
        raise HTTPException(
            status_code=400,
            detail="User already has a student profile"
        )

    existing_student = (
        db.query(Student)
        .filter(Student.student_id == student_data.student_id)
        .first()
    )

    if existing_student:
        raise HTTPException(
            status_code=400,
            detail="Student ID already exists"
        )

    existing_email = (
        db.query(Student)
        .filter(Student.email == student_data.email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Student email already exists"
        )

    department = (
        db.query(Department)
        .filter(Department.id == student_data.department_id)
        .first()
    )

    if department is None:
        raise HTTPException(
            status_code=404,
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    students = db.query(Student).all()

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
            status_code=404,
            detail="Student profile not found"
        )

    return student

@router.get(
    "/search",
    response_model=list[StudentResponse]
)
def search_students(
    query: str,
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
            status_code=404,
            detail="Student not found"
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
            status_code=404,
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
                status_code=404,
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
                status_code=400,
                detail="Student email already exists"
            )

    for field, value in update_data.items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)

    return student


@router.delete("/{student_id}")
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
            status_code=404,
            detail="Student not found"
        )

    db.delete(student)
    db.commit()

    return {
        "message": "Student deleted successfully"
    }