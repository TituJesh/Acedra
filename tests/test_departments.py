from fastapi import status
from app.models.department import Department


def test_create_department_as_admin(client, admin_headers):
    """Test department creation by admin."""
    payload = {
        "name": "Electrical and Electronics Engineering",
        "code": "EEE"
    }
    response = client.post("/departments/", json=payload, headers=admin_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["code"] == payload["code"]
    assert "id" in data


def test_create_department_as_student_forbidden(client, student_headers):
    """Test department creation by student returns 403."""
    payload = {
        "name": "Mechanical Engineering",
        "code": "MECH"
    }
    response = client.post("/departments/", json=payload, headers=student_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_create_duplicate_department_name(client, admin_headers, test_department):
    """Test creating a department with existing name returns 400."""
    payload = {
        "name": test_department.name,
        "code": "DIFF"
    }
    response = client.post("/departments/", json=payload, headers=admin_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Department name already exists"


def test_create_duplicate_department_code(client, admin_headers, test_department):
    """Test creating a department with existing code returns 400."""
    payload = {
        "name": "Different Name",
        "code": test_department.code
    }
    response = client.post("/departments/", json=payload, headers=admin_headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Department code already exists"


def test_get_departments_list(client, student_headers, test_department):
    """Test retrieving list of departments."""
    response = client.get("/departments/", headers=student_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert any(d["id"] == test_department.id for d in data)


def test_get_department_by_id(client, student_headers, test_department):
    """Test getting single department by id."""
    response = client.get(f"/departments/{test_department.id}", headers=student_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == test_department.name


def test_get_department_not_found(client, student_headers):
    """Test getting a non-existent department returns 404."""
    response = client.get("/departments/9999", headers=student_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Department not found"


def test_update_department_as_admin(client, admin_headers, test_department):
    """Test updating a department by admin."""
    payload = {"name": "Computer Science & Artificial Intelligence"}
    response = client.put(
        f"/departments/{test_department.id}",
        json=payload,
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == payload["name"]


def test_update_department_as_student_forbidden(client, student_headers, test_department):
    """Test updating department by student is forbidden."""
    response = client.put(
        f"/departments/{test_department.id}",
        json={"name": "New Name"},
        headers=student_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_update_department_duplicate_conflict(client, admin_headers, db_session, test_department):
    """Test updating department name to match another department returns 400."""
    other_dept = Department(name="Civil Engineering", code="CIVIL")
    db_session.add(other_dept)
    db_session.commit()

    response = client.put(
        f"/departments/{test_department.id}",
        json={"name": "Civil Engineering"},
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Department name already exists"


def test_delete_department_as_admin(client, admin_headers, db_session):
    """Test deleting an empty department."""
    dept = Department(name="Architecture", code="ARCH")
    db_session.add(dept)
    db_session.commit()

    response = client.delete(f"/departments/{dept.id}", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Department deleted successfully"


def test_delete_department_with_students_blocked(client, admin_headers, test_student):
    """Test deleting a department that has active students returns 400."""
    response = client.delete(
        f"/departments/{test_student.department_id}",
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Cannot delete department with students"


def test_delete_department_not_found(client, admin_headers):
    """Test deleting non-existent department returns 404."""
    response = client.delete("/departments/9999", headers=admin_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
