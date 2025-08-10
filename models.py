from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    username: str
    gender: str
    DateOfBirth: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: str = None


class UserProfile(BaseModel):
    email: EmailStr
    gender: str
    DateOfBirth: str
    profile_picture : str = None
    contact_number: str = None
    Address: str = Field(..., alias="address") 
    Facebook: str = Field(..., alias="facebook")
    Instagram: str = Field(..., alias="instagram")
    
class AuditLog(BaseModel):
    action: str
    user_id: str
    timestamp: str
    details: Optional[str] = None   


#containt management system for blogs
class BlogCreate(BaseModel):
    title: str
    content: str  # HTML content
    tags: List[str] = []


class BlogInDB(BaseModel):
    id: str
    author: str
    created_at: datetime
    updated_at: datetime
    media_files: List[str] = []
    title: str
    tags: List[str] = []
    content: str  # HTML content

    class Config:
        orm_mode = True