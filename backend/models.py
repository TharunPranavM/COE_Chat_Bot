from pydantic import BaseModel, EmailStr
from typing import Literal

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Literal['user', 'admin']

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    timestamp: str

class UploadResponse(BaseModel):
    filename: str
    file_id: str
    size: int
    upload_date: str
