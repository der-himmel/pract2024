from fastapi import HTTPException
from typing import List

from fastapi.encoders import jsonable_encoder
from starlette.responses import Response

from app.errors import DATABASE_NOT_UPTODATE, INCORRECT_STAND_DATA
from app.schemas import UploadStand
from app.models import Stand
from sqlalchemy.orm import Session
from fastapi import Depends, UploadFile
from app.utils.db_utils import connect_db
from fastapi import APIRouter
import json
from pydantic import ValidationError
from sqlalchemy import exc

import svgutils
import re

router = APIRouter(
    prefix="/stands",
    tags=["stands"],
    responses={404: {"description": "Not found"}},
)

@router.get('/get_all')
async def get_all_stands(db: Session = Depends(connect_db)):
    try:
        stands = (
            db.query(Stand)
            .all()
        )
    except exc.ProgrammingError as e:
        raise HTTPException(status_code=500, detail=DATABASE_NOT_UPTODATE)

    else:
        return stands
    

@router.post('/create')
async def create_stand(file: UploadFile, db: Session = Depends(connect_db)):
    stand_data = json.load(file.file)

    try:
        UploadStand.model_validate(stand_data)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=INCORRECT_STAND_DATA)

    stand = Stand(stand_data["name"], stand_data["width"], stand_data["height"], stand_data["holes"])

    try:
        db.add(stand)
        db.commit()
    except exc.ProgrammingError as e:
        raise HTTPException(status_code=500, detail=DATABASE_NOT_UPTODATE)

    else:
        return stand.id
