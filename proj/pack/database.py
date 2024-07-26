from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = 'sqlite:///./users.db'
PDF_FILES_DIRECTORY_PATH = '.../pract/proj/pdfdocs'
TOKEN_PATH = ".../proj/pack/tokens/token.txt"
ADMIN_TOKEN_PATH = ".../proj/pack/tokens/admin-token.txt"
PROFILE_PICTURES_PATH = "..."

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

from . import models
models.Base.metadata.create_all(engine) #database

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
