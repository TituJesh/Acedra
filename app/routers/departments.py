from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_admin
from app.models.department import Department
from app.models.user import User
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse
)
from app.utils.logger import logger


router = APIRouter(
    prefix="/departments",
    tags=["Departments"]
)


@router.post(
    "/",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED
)
def create_department(
    department_data: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    existing_name = (
        db.query(Department)
        .filter(Department.name == department_data.name)
        .first()
    )

    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department name already exists"
        )

    existing_code = (
        db.query(Department)
        .filter(Department.code == department_data.code)
        .first()
    )

    if existing_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department code already exists"
        )

    new_department = Department(
        name=department_data.name,
        code=department_data.code
    )

    db.add(new_department)
    db.commit()
    db.refresh(new_department)

    logger.info(
        f"Department created: id={new_department.id}, "
        f"name={new_department.name}, code={new_department.code}"
    )

    return new_department


@router.get(
    "/",
    response_model=list[DepartmentResponse]
)
def get_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Department).all()


@router.get(
    "/{department_id}",
    response_model=DepartmentResponse
)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    department = (
        db.query(Department)
        .filter(Department.id == department_id)
        .first()
    )

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    return department


@router.put(
    "/{department_id}",
    response_model=DepartmentResponse
)
def update_department(
    department_id: int,
    department_data: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    department = (
        db.query(Department)
        .filter(Department.id == department_id)
        .first()
    )

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    update_data = department_data.model_dump(
        exclude_unset=True
    )

    if "name" in update_data:
        existing_name = (
            db.query(Department)
            .filter(
                Department.name == update_data["name"],
                Department.id != department_id
            )
            .first()
        )

        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department name already exists"
            )

    if "code" in update_data:
        existing_code = (
            db.query(Department)
            .filter(
                Department.code == update_data["code"],
                Department.id != department_id
            )
            .first()
        )

        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department code already exists"
            )

    for field, value in update_data.items():
        setattr(department, field, value)

    db.commit()
    db.refresh(department)

    logger.info(
        f"Department updated: id={department_id}"
    )

    return department


@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    department = (
        db.query(Department)
        .filter(Department.id == department_id)
        .first()
    )

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    if department.students:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete department with students"
        )

    db.delete(department)
    db.commit()

    logger.info(
        f"Department deleted: id={department_id}"
    )

    return {
        "message": "Department deleted successfully"
    }