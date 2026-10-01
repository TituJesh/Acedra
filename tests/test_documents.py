import io
from fastapi import status
from app.models.document import Document


def test_upload_document_success(client, admin_headers, test_student, mock_s3_upload):
    """Test successful document upload by admin."""
    file_bytes = b"%PDF-1.4 Mock PDF Content"
    response = client.post(
        f"/documents/upload/{test_student.id}",
        files={"file": ("transcript.pdf", io.BytesIO(file_bytes), "application/pdf")},
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["student_id"] == test_student.id
    assert data["file_name"] == "transcript.pdf"
    assert data["file_type"] == "application/pdf"
    assert "s3_key" in data
    mock_s3_upload.assert_called_once()


def test_upload_document_as_student_forbidden(client, student_headers, test_student):
    """Test student role is forbidden from uploading documents."""
    response = client.post(
        f"/documents/upload/{test_student.id}",
        files={"file": ("test.pdf", io.BytesIO(b"test"), "application/pdf")},
        headers=student_headers
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_upload_document_student_not_found(client, admin_headers):
    """Test uploading document for non-existent student returns 404."""
    response = client.post(
        "/documents/upload/9999",
        files={"file": ("test.pdf", io.BytesIO(b"test"), "application/pdf")},
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_upload_document_unsupported_extension(client, admin_headers, test_student):
    """Test uploading unsupported file format returns 400."""
    response = client.post(
        f"/documents/upload/{test_student.id}",
        files={"file": ("script.sh", io.BytesIO(b"echo hi"), "application/x-sh")},
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "not supported" in response.json()["detail"]


def test_get_student_documents_as_admin(client, admin_headers, db_session, test_student):
    """Test admin can retrieve all documents for a student."""
    doc = Document(
        student_id=test_student.id,
        file_name="diploma.pdf",
        file_type="application/pdf",
        s3_key=f"students/{test_student.id}/diploma.pdf"
    )
    db_session.add(doc)
    db_session.commit()

    response = client.get(f"/documents/student/{test_student.id}", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert data[0]["file_name"] == "diploma.pdf"


def test_get_student_documents_as_owner(client, student_headers, db_session, test_student):
    """Test student owner can retrieve their own documents."""
    doc = Document(
        student_id=test_student.id,
        file_name="id_card.png",
        file_type="image/png",
        s3_key=f"students/{test_student.id}/id_card.png"
    )
    db_session.add(doc)
    db_session.commit()

    response = client.get(f"/documents/student/{test_student.id}", headers=student_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert any(d["file_name"] == "id_card.png" for d in data)


def test_get_student_documents_as_other_student_forbidden(client, other_student_headers, db_session, test_student):
    """Test student cannot view documents of another student."""
    doc = Document(
        student_id=test_student.id,
        file_name="grade_report.pdf",
        file_type="application/pdf",
        s3_key=f"students/{test_student.id}/grade_report.pdf"
    )
    db_session.add(doc)
    db_session.commit()

    response = client.get(f"/documents/student/{test_student.id}", headers=other_student_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_document_by_id(client, admin_headers, db_session, test_student):
    """Test retrieving document by its primary key ID."""
    doc = Document(
        student_id=test_student.id,
        file_name="record.docx",
        file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        s3_key=f"students/{test_student.id}/record.docx"
    )
    db_session.add(doc)
    db_session.commit()

    response = client.get(f"/documents/{doc.id}", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["file_name"] == "record.docx"


def test_download_document_presigned_url(client, admin_headers, db_session, test_student, mock_s3_download):
    """Test generating a presigned download URL for a document."""
    doc = Document(
        student_id=test_student.id,
        file_name="syllabus.pdf",
        file_type="application/pdf",
        s3_key=f"students/{test_student.id}/syllabus.pdf"
    )
    db_session.add(doc)
    db_session.commit()

    response = client.get(f"/documents/{doc.id}/download", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["file_name"] == "syllabus.pdf"
    assert "download_url" in data
    assert data["expires_in"] == 300
    mock_s3_download.assert_called_once_with(doc.s3_key)


def test_download_document_as_other_student_forbidden(client, other_student_headers, db_session, test_student):
    """Test non-owner student cannot download another student's document."""
    doc = Document(
        student_id=test_student.id,
        file_name="secret.pdf",
        file_type="application/pdf",
        s3_key=f"students/{test_student.id}/secret.pdf"
    )
    db_session.add(doc)
    db_session.commit()

    response = client.get(f"/documents/{doc.id}/download", headers=other_student_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_document_as_admin(client, admin_headers, db_session, test_student, mock_s3_delete):
    """Test admin deleting a document removes DB record and triggers S3 deletion."""
    doc = Document(
        student_id=test_student.id,
        file_name="to_delete.pdf",
        file_type="application/pdf",
        s3_key=f"students/{test_student.id}/to_delete.pdf"
    )
    db_session.add(doc)
    db_session.commit()

    response = client.delete(f"/documents/{doc.id}", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Document deleted successfully"
    mock_s3_delete.assert_called_once_with(doc.s3_key)

    # Verify document no longer exists
    assert db_session.query(Document).filter(Document.id == doc.id).first() is None


def test_delete_document_as_student_forbidden(client, student_headers, db_session, test_student):
    """Test students cannot delete documents."""
    doc = Document(
        student_id=test_student.id,
        file_name="keep_me.pdf",
        file_type="application/pdf",
        s3_key=f"students/{test_student.id}/keep_me.pdf"
    )
    db_session.add(doc)
    db_session.commit()

    response = client.delete(f"/documents/{doc.id}", headers=student_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_document_not_found(client, admin_headers):
    """Test deleting non-existent document returns 404."""
    response = client.delete("/documents/9999", headers=admin_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
