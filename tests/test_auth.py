from fastapi import status
from app.models.user import User


def test_register_admin_success(client):
    """Test successful registration of an admin user."""
    payload = {
        "username": "new_admin",
        "email": "new_admin@acedra.edu",
        "password": "SecurePassword123!",
        "role": "admin"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["username"] == "new_admin"
    assert data["email"] == "new_admin@acedra.edu"
    assert data["role"] == "admin"
    assert "user_id" in data


def test_register_student_success(client):
    """Test successful registration of a student user."""
    payload = {
        "username": "new_student",
        "email": "new_student@acedra.edu",
        "password": "SecurePassword123!",
        "role": "student"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["username"] == "new_student"
    assert data["role"] == "student"


def test_register_duplicate_username(client, admin_user):
    """Test registering a user with an existing username returns 400."""
    payload = {
        "username": admin_user.username,
        "email": "unique_email@acedra.edu",
        "password": "Password123!",
        "role": "student"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Username already registered"


def test_register_duplicate_email(client, admin_user):
    """Test registering a user with an existing email returns 400."""
    payload = {
        "username": "unique_username",
        "email": admin_user.email,
        "password": "Password123!",
        "role": "student"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Email already registered"


def test_register_invalid_role(client):
    """Test registering with an unsupported role returns 400."""
    payload = {
        "username": "faculty_user",
        "email": "faculty@acedra.edu",
        "password": "Password123!",
        "role": "instructor"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Role must be either 'admin' or 'student'" in response.json()["detail"]


def test_register_invalid_email_format(client):
    """Test registering with an invalid email returns 422."""
    payload = {
        "username": "invalid_email_user",
        "email": "not-an-email",
        "password": "Password123!",
        "role": "student"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_login_success(client, admin_user):
    """Test login with valid credentials returns JWT token."""
    response = client.post(
        "/auth/login",
        data={
            "username": admin_user.username,
            "password": "AdminPass123!"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, admin_user):
    """Test login with incorrect password returns 401."""
    response = client.post(
        "/auth/login",
        data={
            "username": admin_user.username,
            "password": "WrongPassword999!"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid username or password"


def test_login_nonexistent_user(client):
    """Test login with non-existent username returns 401."""
    response = client.post(
        "/auth/login",
        data={
            "username": "does_not_exist",
            "password": "SomePassword123!"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid username or password"


def test_get_me_success(client, student_user, student_headers):
    """Test /auth/me returns current user details."""
    response = client.get("/auth/me", headers=student_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == student_user.username
    assert data["email"] == student_user.email
    assert data["role"] == student_user.role


def test_get_me_unauthenticated(client):
    """Test /auth/me without token returns 401."""
    response = client.get("/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_invalid_token(client):
    """Test /auth/me with invalid Bearer token returns 401."""
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.value"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_admin_test_as_admin(client, admin_headers, admin_user):
    """Test /auth/admin-test is accessible to admins."""
    response = client.get("/auth/admin-test", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "Welcome Admin"
    assert data["username"] == admin_user.username
    assert data["role"] == "admin"


def test_admin_test_as_student_forbidden(client, student_headers):
    """Test /auth/admin-test is forbidden to student accounts."""
    response = client.get("/auth/admin-test", headers=student_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Admin access required"
