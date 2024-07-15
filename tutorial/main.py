from typing import Annotated
from fastapi import FastAPI, Depends, status, Response, Request, Form, File, UploadFile, APIRouter
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from datetime import datetime
import os

from pack import schemas, models
from pack.database import engine, SessionLocal, PDF_FILES_DIRECTORY_PATH

app = FastAPI()
models.Base.metadata.create_all(engine) #database
templates = Jinja2Templates(directory="templates")  #html templates

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/auth", status_code=status.HTTP_200_OK, response_class=HTMLResponse)
async def authenticate(request: Request):
    return templates.TemplateResponse("authenticate.html", {"request": request})

@app.post("/auth", status_code=status.HTTP_202_ACCEPTED, response_class=RedirectResponse)
async def authenticate_post(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        return RedirectResponse(url=f"/users/{user.id}", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(url="/auth", status_code=status.HTTP_404_NOT_FOUND)

@app.get("/register", status_code=status.HTTP_200_OK, response_class=HTMLResponse)   #регистрация нового пользователя
async def form_post(request: Request):
    return templates.TemplateResponse('register.html', context={'request': request})

@app.post("/register", status_code=status.HTTP_201_CREATED, response_class=RedirectResponse)
async def form_post(request: Request,
              fsurname: str = Form(...),
              fname: str = Form(...),
              fpatronym: str = Form(...),
              fbdate: str = Form(...),
              femail: str = Form(...),
              fdocs: UploadFile = File(),
              db: Session = Depends(get_db)):
    if fdocs:
        docpath = os.path.join(PDF_FILES_DIRECTORY_PATH, fdocs.filename)
        with open(docpath, "wb") as file:
            file.write(fdocs.file.read())
    new_user = models.User(surname=fsurname,
                           name=fname,
                           patronym=fpatronym,
                           bdate=datetime.strptime(fbdate, "%Y-%m-%d"),
                           email=femail,
                           docs=docpath)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return RedirectResponse(url=f'/users/{new_user.id}', status_code=status.HTTP_303_SEE_OTHER)
    # snp = fsurname + ' ' + fname + ' ' + fpatronym
    # return templates.TemplateResponse('user.html',
    #                                   context={'request': request,
    #                                             'snp': snp,
    #                                             'bdate': new_user.bdate.strftime("%d/%m/%Y"),
    #                                             'email': new_user.email,
    #                                             'docs': new_user.docs})

@app.get('/users/{id}', status_code=status.HTTP_200_OK, response_class=HTMLResponse)
async def fetch_by_id(request: Request, id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        Response.status_code = status.HTTP_404_NOT_FOUND
        return f'Пользователя с id {id} еще не существует...'
    else:
        snp = user.surname + ' ' + user.name + ' ' + user.patronym
        return templates.TemplateResponse(request=request,
                                          name="user.html",
                                          context={ 'id': id,
                                                    'snp': snp,
                                                   'bdate': user.bdate.strftime("%d/%m/%Y"),
                                                    'email': user.email,
                                                    'docs': user.docs})

@app.get("/users/{id}/files", status_code=status.HTTP_200_OK)
async def download_docs(id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        Response.status_code = status.HTTP_404_NOT_FOUND
        return f'Пользователь с id {id} не загрузил файл...'
    else:
        print(user.email.split('@', 0))
        return FileResponse(path=user.docs,
                            media_type='application/pdf',
                            filename=user.email.split('@', 0)[0] + '.pdf')
