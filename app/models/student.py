from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    student_id = Column(String(20), unique=True, nullable=False, index=True)

    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)

    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(15))

    date_of_birth = Column(Date)
    gender = Column(String(20))

    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=False
    )

    year = Column(Integer)

    address = Column(String(255))

    user = relationship("User", back_populates="student")

    department = relationship("Department", back_populates="students")

    documents = relationship(
        "Document",
        back_populates="student",
        cascade="all, delete-orphan"
    )