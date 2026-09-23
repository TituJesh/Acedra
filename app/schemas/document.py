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