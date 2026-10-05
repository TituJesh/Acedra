from fastapi import status
from app.models.user import User
from app.utils.security import hash_password


def test_create_student_as_admin(client, admin_headers, student_user, test_department):
    """Test successful student profile creation by an administrator."""
    payload = {
        "user_id": student_user.id,
        "student_id": "STU_UNIQUE_001",
        "first_name": "Alice",
        "last_name": "Walker",
        "email": "alice.unique@acedra.edu",
        "phone": "+1234567890",
        "date_of_birth": "2004-03-15",
        "gender": "Female",
        "department_id": test_department.id,
        "year": 1,
        "address": "456 College Road"
    }
    response = client.post("/students/", json=payload, headers=admin_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["student_id"] == "STU_UNIQUE_001"
    assert data["first_name"] == "Alice"
    assert data["user_id"] == student_user.id


def test_create_student_as_student_forbidden(client, student_headers, student_user, test_department):
    """Test student role cannot create a student profile."""
    payload = {
        "user_id": student_user.id,
        "student_id": "STU_FORBIDDEN",
        "first_name": "Bob",
        "last_name": "Smith",
        "email": "bob@acedra.edu",
        "department_id": test_department.id
    }
    response = client.post("/students/", json=payload, headers=student_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_student_user_not_found(client, admin_headers, test_department):
    """Test creating student for non-existent user returns 404."""
    payload = {
        "user_id": 99999,
        "student_id": "STU_NO_USER",
        "first_name": "Ghost",
        "last_name": "User",
        "email": "ghost@acedra.edu",
        "department_id": test_department.id
    }
    response = client.post("/students/", json=payload, headers=admin_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "User not found"


def test_create_student_user_not_student_role(client, admin_headers, admin_user, test_department):
    """Test creating student for a user with admin role returns 400."""
    payload = {
        "user_id": admin_user.id,
        "student_id": "STU_ADMIN_USER",
        "first_name": "Admin",
        "last_name": "Person",
        "email": "admin.profile@acedra.edu",
        "department_id": test_department.id
    }
    response = client.post("/students/", json=payload, headers=admin_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "User must have student role"


def test_create_student_duplicate_user_profile(client, admin_headers, test_student, test_department):
    """Test creating a second student profile for the same user returns 400."""
    payload = {
        "user_id": test_student.user_id,
        "student_id": "STU_DIFF_ID",
        "first_name": "Duplicate",
        "last_name": "User",
        "email": "different.email@acedra.edu",
        "department_id": test_department.id
    }
    response = client.post("/students/", json=payload, headers=admin_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "User already has a student profile"


def test_create_student_duplicate_student_id(client, admin_headers, test_student, other_student_user, test_department):
    """Test creating student with duplicate student_id returns 400."""
    payload = {
        "user_id": other_student_user.id,
        "student_id": test_student.student_id,
        "first_name": "New",
        "last_name": "Name",
        "email": "unique.new@acedra.edu",
        "department_id": test_department.id
    }
    response = client.post("/students/", json=payload, headers=admin_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Student ID already exists"


def test_create_student_duplicate_email(client, admin_headers, test_student, other_student_user, test_department):
    """Test creating student with duplicate email returns 400."""
    payload = {
        "user_id": other_student_user.id,
        "student_id": "STU_BRAND_NEW",
        "first_name": "New",
        "last_name": "Name",
        "email": test_student.email,
        "department_id": test_department.id
    }
    response = client.post("/students/", json=payload, headers=admin_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Student email already exists"


def test_create_student_department_not_found(client, admin_headers, student_user):
    """Test creating student with non-existent department returns 404."""
    payload = {
        "user_id": student_user.id,
        "student_id": "STU_NO_DEPT",
        "first_name": "No",
        "last_name": "Dept",
        "email": "nodept@acedra.edu",
        "department_id": 8888
    }
    response = client.post("/students/", json=payload, headers=admin_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Department not found"


def test_get_students_list(client, admin_headers, test_student):
    """Test retrieving list of all students."""
    response = client.get("/students/", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert any(s["id"] == test_student.id for s in data)


def test_get_students_filter_by_department(client, admin_headers, test_student):
    """Test filtering students by department_id."""
    response = client.get(
        f"/students/?department_id={test_student.department_id}",
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert all(s["department_id"] == test_student.department_id for s in data)


def test_get_student_by_id_as_admin(client, admin_headers, test_student):
    """Test admin can view any student profile."""
    response = client.get(f"/students/{test_student.id}", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["student_id"] == test_student.student_id


def test_get_student_by_id_as_owner(client, student_headers, test_student):
    """Test student owner can view their own student profile."""
    response = client.get(f"/students/{test_student.id}", headers=student_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["student_id"] == test_student.student_id


def test_get_student_by_id_as_other_student_forbidden(client, other_student_headers, test_student):
    """Test non-admin student cannot view another student's profile."""
    response = client.get(f"/students/{test_student.id}", headers=other_student_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Access forbidden" in response.json()["detail"]


def test_get_my_profile(client, student_headers, test_student):
    """Test student can retrieve their own profile via /students/me."""
    response = client.get("/students/me", headers=student_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["student_id"] == test_student.student_id


def test_get_my_profile_not_found(client, other_student_headers):
    """Test /students/me returns 404 when student profile is not yet created."""
    response = client.get("/students/me", headers=other_student_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Student profile not found"


def test_search_students(client, admin_headers, test_student):
    """Test searching students by keyword."""
    response = client.get(f"/students/search?query={test_student.first_name}", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert any(s["first_name"] == test_student.first_name for s in data)


def test_update_student_as_admin(client, admin_headers, test_student):
    """Test updating student details by admin."""
    payload = {
        "phone": "+9876543210",
        "address": "Updated Campus Address 999"
    }
    response = client.put(f"/students/{test_student.id}", json=payload, headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["phone"] == "+9876543210"
    assert data["address"] == "Updated Campus Address 999"


def test_update_student_as_student_forbidden(client, student_headers, test_student):
    """Test student cannot update student records."""
    response = client.put(
        f"/students/{test_student.id}",
        json={"phone": "+0000000000"},
        headers=student_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_student_as_admin(client, admin_headers, test_student):
    """Test deleting student record by admin."""
    response = client.delete(f"/students/{test_student.id}", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Student deleted successfully"


def test_delete_student_as_student_forbidden(client, student_headers, test_student):
    """Test deleting student record by student is forbidden."""
    response = client.delete(f"/students/{test_student.id}", headers=student_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_student_not_found(client, admin_headers):
    """Test deleting non-existent student returns 404."""
    response = client.delete("/students/9999", headers=admin_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_student_by_id_not_found(client, admin_headers):
    """Test retrieving non-existent student by ID returns 404."""
    response = client.get("/students/99999", headers=admin_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Student not found"


def test_search_students_no_results(client, admin_headers):
    """Test searching with unmatched query returns an empty list."""
    response = client.get("/students/search?query=NonExistentMatchXYZ", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_update_student_not_found(client, admin_headers):
    """Test updating non-existent student returns 404."""
    response = client.put(
        "/students/99999",
        json={"first_name": "Ghost"},
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Student not found"


def test_update_student_department_not_found(client, admin_headers, test_student):
    """Test updating student with non-existent department returns 404."""
    response = client.put(
        f"/students/{test_student.id}",
        json={"department_id": 99999},
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Department not found"


def test_update_student_duplicate_email(client, admin_headers, test_student, other_student_user, test_department, db_session):
    """Test updating student email to another student's existing email returns 400."""
    import datetime
    from app.models.student import Student

    second_student = Student(
        user_id=other_student_user.id,
        student_id="STU_SECOND_002",
        first_name="Jane",
        last_name="Smith",
        email="jane.smith.student@acedra.edu",
        department_id=test_department.id,
        year=2
    )
    db_session.add(second_student)
    db_session.commit()

    response = client.put(
        f"/students/{test_student.id}",
        json={"email": "jane.smith.student@acedra.edu"},
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Student email already exists" in response.json()["detail"]


def test_get_students_filter_by_year(client, admin_headers, test_student):
    """Test filtering students by academic year."""
    response = client.get(f"/students/?year={test_student.year}", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert all(s["year"] == test_student.year for s in data)

    # Non-matching year
    resp_empty = client.get("/students/?year=6", headers=admin_headers)
    assert resp_empty.status_code == status.HTTP_200_OK
    assert resp_empty.json() == []


def test_get_students_filter_by_gender(client, admin_headers, test_student):
    """Test filtering students by gender."""
    response = client.get(f"/students/?gender={test_student.gender}", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert all(s["gender"] == test_student.gender for s in data)

    # Non-matching gender
    resp_empty = client.get("/students/?gender=NonExistentGender", headers=admin_headers)
    assert resp_empty.status_code == status.HTTP_200_OK
    assert resp_empty.json() == []


def test_get_student_stats_summary_as_admin(client, admin_headers, test_student, test_department):
    """Test admin can retrieve student demographic and departmental stats."""
    response = client.get("/students/stats/summary", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_students" in data
    assert data["total_students"] >= 1
    assert "students_by_year" in data
    assert str(test_student.year) in data["students_by_year"]
    assert "students_by_gender" in data
    assert test_student.gender in data["students_by_gender"]
    assert "students_by_department" in data
    assert any(dept["department_id"] == test_department.id and dept["student_count"] >= 1 for dept in data["students_by_department"])


def test_get_student_stats_summary_as_student(client, student_headers):
    """Test authenticated student can view statistics summary."""
    response = client.get("/students/stats/summary", headers=student_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_students" in data


def test_get_student_stats_summary_unauthenticated(client):
    """Test unauthenticated request to stats summary returns 401."""
    response = client.get("/students/stats/summary")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


