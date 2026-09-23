from datetime import date
from pydantic import BaseModel, EmailStr
from pydantic import ConfigDict


class DepartmentInfo(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class StudentCreate(BaseModel):
    user_id: int
    student_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    department_id: int
    year: int | None = None
    address: str | None = None


class StudentUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    department_id: int | None = None
    year: int | None = None
    address: str | None = None


class StudentResponse(BaseModel):
    id: int
    user_id: int
    student_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    department_id: int
    year: int | None = None
    address: str | None = None
    department: DepartmentInfo

    model_config = ConfigDict(from_attributes=True)