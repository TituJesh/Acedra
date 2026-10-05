import os
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_admin
from app.models.document import Document
from app.models.student import Student
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.document import DocumentDownloadResponse, DocumentResponse
from app.services.s3_service import (
    delete_file_from_s3,
    generate_download_url,
    upload_file_to_s3,
)
from app.utils.logger import logger

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".txt"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


@router.get(
    "/",
    response_model=list[DocumentResponse]
)
def get_documents(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    student_id: int | None = Query(None, description="Filter by student ID"),
    file_type: str | None = Query(None, description="Filter by MIME file type"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Document)
    if student_id is not None:
        query = query.filter(Document.student_id == student_id)
    if file_type is not None:
        query = query.filter(Document.file_type == file_type)

    return query.offset(skip).limit(limit).all()


@router.post(
    "/upload/{student_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED
)
def upload_document(
    student_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is missing"
        )

    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' is not supported. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if file.size and file.size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB"
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

    logger.info(
        f"Document uploaded: student_id={student_id}, "
        f"file_name={document.file_name}"
    )

    return document


@router.get(
    "/student/{student_id}",
    response_model=list[DocumentResponse]
)
def get_student_documents(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    if current_user.role != "admin" and student.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: cannot view other student documents"
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    student = db.query(Student).filter(Student.id == document.student_id).first()
    if current_user.role != "admin" and (student is None or student.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: cannot view this document"
        )

    return document


@router.get(
    "/{document_id}/download",
    response_model=DocumentDownloadResponse
)
def download_document(
    document_id: int,
    expires_in: int = Query(300, ge=60, le=3600, description="URL expiration time in seconds (60-3600)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    student = db.query(Student).filter(Student.id == document.student_id).first()
    if current_user.role != "admin" and (student is None or student.user_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: cannot download this document"
        )

    if expires_in != 300:
        download_url = generate_download_url(
            document.s3_key,
            expiration=expires_in
        )
    else:
        download_url = generate_download_url(
            document.s3_key
        )

    return {
        "file_name": document.file_name,
        "download_url": download_url,
        "expires_in": expires_in
    }


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK
)
def delete_document(
    document_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    delete_file_from_s3(document.s3_key)

    db.delete(document)
    db.commit()

    logger.info(
        f"Document deleted: document_id={document_id}"
    )

    return {
        "message": "Document deleted successfully"
    }