from pydantic import BaseModel
import datetime

class User(BaseModel):
    surname: str
    name: str
    patronym: str
    bdate: datetime.date
    email: str
    hashed_password: str
    cookie: str
    docs: str
