from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    message: str

    model_config = ConfigDict(from_attributes=True)
