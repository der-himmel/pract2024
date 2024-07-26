from datetime import datetime, timedelta, timezone
from typing import Annotated, Union
from pydantic import BaseModel

import jwt
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status, Request
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key

from . import schemas, models
from .database import engine, SessionLocal, TOKEN_PATH, ADMIN_TOKEN_PATH
from .certificates import gen

models.Base.metadata.create_all(engine)

SECRET_KEY = "pract2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
keys = gen.AuthJWT()

with open(keys.PUBLIC_KEY_PATH, 'rb') as pub_file:
    public_key = load_pem_public_key(
        pub_file.read(),
        backend=default_backend()
    )

with open(keys.PRIVATE_KEY_PATH, 'rb') as prv_file:
    private_key = load_pem_private_key(
        prv_file.read(),
        password=None,
        backend=default_backend()
    )

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

generator = SessionLocal()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(email: str,
             db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user == None:
        raise HTTPException(
            status_code=404,
            detail=f'Пользователь с почтой {email} не найден...'
        )
    else:
        return user

def authenticate_user(
        username: str,
        password: str,
        db: Session = Depends(get_db),
        response_class=HTMLResponse
):
    check = if_plebs(username, db)
    if not check:
        user = get_user(username, db)
        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=401,
                detail=f'Неверный пароль...'
        )
        return user
    else:
        return check

def create_access_token(
        data: dict,
        isadmin,
        expires_delta: Union[timedelta, None] = None
):
    if isadmin == False:
        tokenpath = TOKEN_PATH
    else:
        tokenpath = ADMIN_TOKEN_PATH
    open(tokenpath, 'wb').close()  # clear the token
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    # encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    encoded_jwt = jwt.encode(to_encode, private_key, algorithm="RS256")

    with open(tokenpath, "wb") as file:
        file.write(encoded_jwt.encode("utf-8"))
        file.close()
    return encoded_jwt

def decode_access_token(
        token: str,
        isadmin
):
    if isadmin == False:
        tokenpath = TOKEN_PATH
    else:
        tokenpath = ADMIN_TOKEN_PATH
    try:
        # decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        decoded_token = jwt.decode(token, public_key, algorithms=["RS256"])

        user = get_user(decoded_token["sub"], generator)
        return user
    except jwt.ExpiredSignatureError:
        open(tokenpath, 'w').close()  # clear the token
        raise HTTPException(
            status_code=403,
            detail=f'Срок действия предыдущей сессии истек...'
        )
    except jwt.InvalidTokenError:
        open(tokenpath, 'w').close()  # clear the token
        raise HTTPException(
            status_code=403,
            detail=f'Неправильный токен...'
        )

def logout_session():
    open(ADMIN_TOKEN_PATH, 'w').close()
    open(TOKEN_PATH, 'w').close()

def if_plebs(
        username: str,
        db: Session = Depends(get_db),
        response_class=HTMLResponse
):
    admin = db.query(models.Admin).filter(models.Admin.email == username).first()
    if admin == None:
        return False
    else:
        return admin

