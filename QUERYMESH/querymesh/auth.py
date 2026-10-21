"""JWT login: POST /token gives a signed token; every protected call must send it."""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from querymesh import config

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {"sub": username, "iat": now, "exp": now + timedelta(minutes=config.JWT_MINUTES)}
    return jwt.encode(claims, config.JWT_SECRET, algorithm="HS256")


def check_password(username: str, password: str) -> bool:
    return username == config.API_USERNAME and password == config.API_PASSWORD


def current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        claims = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    return claims["sub"]
