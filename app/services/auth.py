from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_JWT_ALGORITHM = "HS256"
_security = HTTPBearer()


def create_access_token(email: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {"sub": email, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_security)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired, please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid authentication token")

    return payload["sub"]
