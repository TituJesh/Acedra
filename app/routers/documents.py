from app.services.s3_service import (
    upload_file_to_s3,
    delete_file_from_s3,
    generate_download_url
)
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.dependencies import get_current_user, require_admin
from app.models.document import Document
from app.models.student import Student
from app.schemas.document import DocumentResponse


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)



def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/upload/{student_id}",
    response_model=DocumentResponse
)
def upload_document(
    student_id: int,
    file: UploadFile = File(...),
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is missing"
        )

    unique_filename = f"{uuid4()}_{file.filename}"

    s3_key = f"students/{student_id}/{unique_filename}"

    upload_file_to_s3(
        file.file,
        s3_key,
        file.content_type
    )

    document = Document(
        student_id=student_id,
        file_name=file.filename,
        file_type=file.content_type,
        s3_key=s3_key
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document

@router.get(
    "/student/{student_id}",
    response_model=list[DocumentResponse]
)
def get_student_documents(
    student_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    documents = db.query(Document).filter(
        Document.student_id == student_id
    ).all()

    return documents

@router.get(
    "/{document_id}",
    response_model=DocumentResponse
)
def get_document(
    document_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    return document

@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    download_url = generate_download_url(
        document.s3_key
    )

    return {
        "file_name": document.file_name,
        "download_url": download_url,
        "expires_in": 300
    }

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    current_user=Depends(require_admin),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    delete_file_from_s3(document.s3_key)

    db.delete(document)
    db.commit()

    return {
        "message": "Document deleted successfully"
    }