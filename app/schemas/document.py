from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    id: int
    student_id: int
    file_name: str
    file_type: str | None = None
    s3_key: str
    uploaded_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentDownloadResponse(BaseModel):
    file_name: str
    download_url: str
    expires_in: int

    model_config = ConfigDict(from_attributes=True)

