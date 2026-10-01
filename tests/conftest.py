import datetime
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Enforce testing environment before importing app modules
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "acedra-test-secret-key-for-pytest-suite-32-chars"
os.environ["AWS_REGION"] = "ap-south-1"
os.environ["S3_BUCKET_NAME"] = "test-acedra-documents-bucket"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.models.department import Department
from app.models.document import Document
from app.models.student import Student
from app.models.user import User
from app.utils.jwt import create_access_token
from app.utils.security import hash_password


TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


@pytest.fixture(scope="function")
def db_session():
    """Create a pristine in-memory database schema for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Provide a TestClient with overridden database session."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session) -> User:
    """Create and persist an administrator user."""
    user = User(
        username="admin_tester",
        email="admin_tester@acedra.edu",
        password_hash=hash_password("AdminPass123!"),
        role="admin"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Generate a JWT token for the admin user."""
    return create_access_token({"user_id": admin_user.id, "role": admin_user.role})


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    """Provide authorization header dictionary for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def student_user(db_session) -> User:
    """Create and persist a student account."""
    user = User(
        username="john_doe",
        email="john.doe@acedra.edu",
        password_hash=hash_password("StudentPass123!"),
        role="student"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student_token(student_user: User) -> str:
    """Generate a JWT token for the student user."""
    return create_access_token({"user_id": student_user.id, "role": student_user.role})


@pytest.fixture
def student_headers(student_token: str) -> dict[str, str]:
    """Provide authorization header dictionary for student user."""
    return {"Authorization": f"Bearer {student_token}"}


@pytest.fixture
def other_student_user(db_session) -> User:
    """Create and persist a second student account for boundary/isolation testing."""
    user = User(
        username="jane_smith",
        email="jane.smith@acedra.edu",
        password_hash=hash_password("OtherPass123!"),
        role="student"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_student_token(other_student_user: User) -> str:
    """Generate a JWT token for the other student user."""
    return create_access_token({"user_id": other_student_user.id, "role": other_student_user.role})


@pytest.fixture
def other_student_headers(other_student_token: str) -> dict[str, str]:
    """Provide authorization header dictionary for other student user."""
    return {"Authorization": f"Bearer {other_student_token}"}


@pytest.fixture
def test_department(db_session) -> Department:
    """Create and persist a default department."""
    department = Department(
        name="Computer Science & Engineering",
        code="CSE"
    )
    db_session.add(department)
    db_session.commit()
    db_session.refresh(department)
    return department


@pytest.fixture
def test_student(db_session, student_user: User, test_department: Department) -> Student:
    """Create and persist a student record linked to student_user and test_department."""
    student = Student(
        user_id=student_user.id,
        student_id="STU2026001",
        first_name="John",
        last_name="Doe",
        email="john.doe.student@acedra.edu",
        phone="+1234567890",
        date_of_birth=datetime.date(2003, 5, 14),
        gender="Male",
        department_id=test_department.id,
        year=3,
        address="123 University Campus, Tech City"
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


@pytest.fixture
def mock_s3_upload():
    """Mock the upload_file_to_s3 service call."""
    with patch("app.routers.documents.upload_file_to_s3") as mock_fn:
        mock_fn.return_value = None
        yield mock_fn


@pytest.fixture
def mock_s3_delete():
    """Mock the delete_file_from_s3 service call."""
    with patch("app.routers.documents.delete_file_from_s3") as mock_fn:
        mock_fn.return_value = None
        yield mock_fn


@pytest.fixture
def mock_s3_download():
    """Mock the generate_download_url service call."""
    with patch("app.routers.documents.generate_download_url") as mock_fn:
        mock_fn.return_value = "https://test-bucket.s3.amazonaws.com/test-key?signature=mock123"
        yield mock_fn


@pytest.fixture
def mock_s3_all(mock_s3_upload, mock_s3_delete, mock_s3_download):
    """Composite fixture providing all S3 mocks."""
    return {
        "upload": mock_s3_upload,
        "delete": mock_s3_delete,
        "download": mock_s3_download,
    }
