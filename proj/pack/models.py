import datetime
from typing import Union, Optional
from fastapi.templating import Jinja2Templates
from sqlalchemy import  Column, Integer, String
from pydantic import BaseModel, FilePath
from sqlalchemy.types import Boolean, Date
from .database import Base

templates = Jinja2Templates(directory="templates")

class User(Base):
    __tablename__ = 'User'

    id = Column(Integer, primary_key=True, index=True)
    surname = Column(String)
    name = Column(String)
    patronym = Column(String)
    bdate = Column(Date)
    email = Column(String)
    hashed_password = Column(String)
    cookie = Column(String)
    docs = Column(String)   #путь к файлу
    pfp = Column(String)

    def to_dict(self):
        return {
            'id': self.id,
            'surname': self.surname,
            'name': self.name,
            'patronym': self.patronym,
            'bdate': self.bdate,
            'email': self.email,
            'hashed_password': self.hashed_password,
            'cookie': self.cookie,
            'docs': self.docs,
            'pfp': self.pfp
        }

class Admin(Base):
    __tablename__ = 'Admin'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String)
    hashed_password = Column(String)
    cookie = Column(String)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'hashed_password': self.hashed_password,
            'cookie': self.cookie,
        }

class Token(Base):
    __tablename__ = 'Token'

    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(String)
    token_type = Column(String)

class TokenData(Base):
    __tablename__ = 'TokenData'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=True)

class AuthJWT(BaseModel):
    PRIVATE_KEY_PATH: FilePath = ".../proj/pack/certificates/private.pem"
    PUBLIC_KEY_PATH: FilePath = ".../proj/pack/certificates/public.pem"
