from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.auth import create_access_token

router = APIRouter()


class LoginRequest(BaseModel):
    email: str


@router.post("/auth/login")
async def login(body: LoginRequest):
    if body.email.strip().lower() != settings.allowed_email.strip().lower():
        raise HTTPException(403, "User is not authorized")

    token = create_access_token(body.email.strip().lower())
    return {"token": token, "token_type": "bearer"}
