import datetime
from sqlalchemy import  Column, Integer, String
from sqlalchemy.types import Boolean, Date
from .database import Base

class User(Base):
    __tablename__ = 'User'

    id = Column(Integer, primary_key=True, index=True)
    surname = Column(String)
    name = Column(String)
    patronym = Column(String)
    bdate = Column(Date)
    email = Column(String)
    docs = Column(String)   #путь к файлу
