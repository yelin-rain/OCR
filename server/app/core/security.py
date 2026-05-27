from datetime import datetime
from datetime import timedelta
from typing import Any, Union

from jose import jwt
from passlib.context import CryptContext


from app.core.config import settings

# Encryption Configuration
PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

# Load secret from settings
SECRET_KEY = settings.SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return PWD_CONTEXT.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return PWD_CONTEXT.hash(password)


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_file_view_token(task_id: int, owner_id: int, expires_hours: int = 24) -> str:
    """供 <img src> 使用的短期任务图片访问令牌（含在 URL 查询参数中）。"""
    expire = datetime.utcnow() + timedelta(hours=expires_hours)
    to_encode = {
        "exp": expire,
        "sub": str(owner_id),
        "task_id": task_id,
        "type": "file_view",
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_file_view_token(token: str, task_id: int) -> int:
    """校验图片访问令牌，返回 owner_id。"""
    from jose import JWTError

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("invalid file token") from exc
    if payload.get("type") != "file_view":
        raise ValueError("invalid file token type")
    if int(payload.get("task_id", -1)) != task_id:
        raise ValueError("task id mismatch")
    owner_id = payload.get("sub")
    if owner_id is None:
        raise ValueError("missing owner")
    return int(owner_id)


def create_refresh_token(
    subject: Union[str, Any], expires_delta: Union[timedelta, None] = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
