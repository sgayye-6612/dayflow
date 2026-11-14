"""Pydantic models: the shape of data coming in and going out of the API.
FastAPI uses them to validate requests (bad input -> 422) and to build the /docs page."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ImageIn(BaseModel):
    src: str = Field(max_length=8_000_000)  # a data URL, up to ~6 MB of image/audio
