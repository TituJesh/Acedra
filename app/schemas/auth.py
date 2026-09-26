from pydantic import BaseModel, ConfigDict, EmailStr


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserRegisterResponse(BaseModel):
    message: str
    user_id: int
    username: str
    email: EmailStr
    role: str

    model_config = ConfigDict(from_attributes=True)

