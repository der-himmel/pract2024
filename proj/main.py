from typing import \
    Annotated, \
    List
from fastapi import \
    FastAPI, \
    Depends, \
    status, \
    Response, \
    Request, \
    Form, \
    File, \
    UploadFile, \
    APIRouter, \
    HTTPException, \
    Header
from fastapi.security import \
    OAuth2PasswordRequestForm
from sqlalchemy.orm import \
    Session
from fastapi.responses import \
    HTMLResponse, \
    FileResponse, \
    RedirectResponse
from fastapi.staticfiles import StaticFiles
from datetime import \
    datetime, \
    timedelta
import requests
import os
import subprocess
import base64

from pack import schemas, models
from pack.database import PDF_FILES_DIRECTORY_PATH, get_db, TOKEN_PATH, ADMIN_TOKEN_PATH
from pack import auth
from pack.certificates import gen
from pack import pfp

app = FastAPI(prefix="/", tags=["Main"])
app.mount("/avatars",
          StaticFiles(directory="D:/users/ivan/Desktop/prev/stud/misc/avatars"),
          name="avatars")
router = APIRouter()
app.include_router(router=gen.router)


# получение формы АУТЕНТИФИКАЦИИ (автоматически проверяет TOKEN)
@app.get("/auth", status_code=status.HTTP_200_OK, response_class=HTMLResponse)
async def authenticate(request: Request):
    if os.path.getsize(TOKEN_PATH) > 0:
        return RedirectResponse(url=f"/users/me", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return models.templates.TemplateResponse("authenticate.html", {"request": request})

# аутентификация С ГЕНЕРАЦИЕЙ ТОКЕНА СЕССИИ
@app.post("/auth",
          status_code=status.HTTP_202_ACCEPTED,
          response_class=RedirectResponse\
          )
async def authenticate_post(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = auth.authenticate_user(form_data.username, form_data.password, db)
    check = auth.if_plebs(form_data.username, db)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Неверное имя пользователя или пароль...",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif check:
        access_token_expires = timedelta(
            minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        access_token = auth.create_access_token(
            data={"sub": user.email},
            isadmin=True,
            expires_delta=access_token_expires,
        )
        return RedirectResponse(url=f"/users/me", status_code=status.HTTP_303_SEE_OTHER)
    else:
        open(ADMIN_TOKEN_PATH, 'wb').close()
        access_token_expires = timedelta(
            minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        access_token = auth.create_access_token(
            data={"sub": user.email},
            isadmin=False,
            expires_delta=access_token_expires
        )
        return RedirectResponse(url=f"/users/me", status_code=status.HTTP_303_SEE_OTHER)


# получение формы для РЕГИСТРАЦИИ нового профиля
@app.get("/register", status_code=status.HTTP_200_OK, response_class=HTMLResponse)
async def form_post(request: Request):
    return models.templates.TemplateResponse('register.html', context={'request': request})

# отправка формы для РЕГИСТРАЦИИ профиля
@app.post("/register", status_code=status.HTTP_201_CREATED, response_class=RedirectResponse)
async def form_post(
        request: Request,
        fsurname: str = Form(...),
        fname: str = Form(...),
        fpatronym: str = Form(...),
        fbdate: str = Form(...),
        femail: str = Form(...),
        fpasswd: str = Form(...),
        fdocs: UploadFile = File(),
        fpfp: UploadFile = File(),
        db: Session = Depends(get_db)
):
    open(ADMIN_TOKEN_PATH, 'wb').close()
    user = db.query(models.User).filter(models.User.email == femail).first()
    if user:
        raise HTTPException(
            status_code=403,
            detail="Пользователь с такой почтой уже есть в системе...",
            headers={"WWW-Authenticate": "Bearer"},
        )
    else:
        if fdocs:
            docpath = os.path.join(PDF_FILES_DIRECTORY_PATH, fdocs.filename)
            with open(docpath, "wb") as file:
                file.write(fdocs.file.read())
                file.close()
        if fpfp and fpfp.filename:
            pfp.save_pfp(
                username=femail,
                pfp=fpfp
            )
            print("PFP SAVED!")
        else:
            pfp.generate_pfp(
                username=femail
            )
        new_user = models.User(
            surname=fsurname,
            name=fname,
            patronym=fpatronym,
            bdate=datetime.strptime(fbdate, "%Y-%m-%d"),
            email=femail,
            hashed_password = auth.get_password_hash(fpasswd),
            docs=docpath,
            pfp=fpfp.filename
        )
        access_token_expires = timedelta(
            minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        access_token = auth.create_access_token(
            data={"sub": new_user.email},
            isadmin=False,
            expires_delta=access_token_expires
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return RedirectResponse(url=f"/users/me", status_code=status.HTTP_303_SEE_OTHER)


@app.get('/users/me',
         status_code=status.HTTP_200_OK,
         response_class=HTMLResponse
)
async def fetch_me(
        request: Request,
):
    if os.path.getsize(ADMIN_TOKEN_PATH) > 0:
        isadmin=True
        return models.templates.TemplateResponse(
            "adminalert.html",
            {"request": request,
             "detail": "У Вас профиль администратора."
             }
        )
    else:
        with open(TOKEN_PATH, "rb") as file:
            access_token = file.read().decode("utf-8")
        file.close()
    granted = auth.decode_access_token(access_token, isadmin=False)
    if granted:
        snp = f"{granted.surname} {granted.name} {granted.patronym}"
        return models.templates.TemplateResponse(
            request=request,
            name="user.html",
            context={
                'id': granted.id,
                'pfp_path': f'{granted.email}.jpg',
                'snp': snp,
                'bdate': granted.bdate.strftime("%d/%m/%Y"),
                'email': granted.email,
                'docs': granted.docs})
    else:
        raise HTTPException(
            status_code=403,
            detail="Отказано в доступе...",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ВЫХОД из профиля и УДАЛЕНИЕ ТОКЕНА СЕССИИ
@app.post("/users/me",
          status_code=status.HTTP_202_ACCEPTED,
          response_class=HTMLResponse
)
@app.post("/users/{id}",
          status_code=status.HTTP_202_ACCEPTED,
          response_class=HTMLResponse
)
def logout_me(
        request: Request
):
    auth.logout_session()   #удаление токена сессии
    return RedirectResponse(url=f"/auth", status_code=status.HTTP_303_SEE_OTHER)


# получение формы для ИЗМЕНЕНИЯ данных профиля
@app.get("/users/me/edit",
         status_code=status.HTTP_200_OK,
         response_class=HTMLResponse
         )
async def edit_my_data(
        request: Request
):
    with open(TOKEN_PATH, "rb") as file:
        access_token = file.read().decode("utf-8")
    file.close()
    my_data = auth.decode_access_token(access_token, isadmin=False)
    if my_data:
        return models.templates.TemplateResponse(
            request=request,
            name="editor.html",
            context={
                'pfp_path': f'{my_data.email}.jpg',
                'surname': my_data.surname,
                'name': my_data.name,
                'patronym': my_data.patronym,
                'bdate': my_data.bdate,
                'email': my_data.email
            }
        )
    else:
        raise HTTPException(
            status_code=404,
            detail="Данные не найдены..."
        )

# ИЗМЕНЕНИЕ данных профиля
@app.post("/users/me/edit",
         status_code=status.HTTP_202_ACCEPTED,
         response_class=HTMLResponse
         )
async def edit_my_data(
        request: Request,
        fsurname: str = Form(...),
        fname: str = Form(...),
        fpatronym: str = Form(...),
        fbdate: str = Form(...),
        fpasswd: str = Form(...),
        femail: str = Form(...),
        db: Session = Depends(get_db)
):
    user = auth.authenticate_user(femail, fpasswd, db)
    if user:
        user.surname = fsurname
        user.name = fname
        user.patronym = fpatronym
        user.bdate = datetime.strptime(fbdate, "%Y-%m-%d")
        db.commit()
        db.refresh(user)
        return RedirectResponse(url=f"/users/me", status_code=status.HTTP_303_SEE_OTHER)
    else:
        raise HTTPException(
            status_code=401,
            detail="Неверный пароль..."
        )


# профиль пользователя ПО АЙДИ
@app.get('/users/{id}', status_code=status.HTTP_200_OK, response_class=HTMLResponse)
async def fetch_by_id(
        request: Request,
        id: int,
        db: Session = Depends(get_db)
):
    # проверка прав администратора для доступа
    if os.path.getsize(ADMIN_TOKEN_PATH) > 0:
        isadmin=True
        with open(ADMIN_TOKEN_PATH, "rb") as file:
            admin_access_token = file.read().decode("utf-8")
        user = db.query(models.User).filter(models.User.id == id).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail=f'Пользователя с id {id} еще не существует...'
            )
        else:
            snp = f'{user.surname} {user.name} {user.patronym}'
            return models.templates.TemplateResponse(request=request,
                                                     name="adminview.html",
                                                     context={'id': id,
                                                              'pfp_path': f'{user.email}.jpg',
                                                              'snp': snp,
                                                              'bdate': user.bdate.strftime("%d/%m/%Y"),
                                                              'email': user.email,
                                                              'docs': user.docs})
    else:
        raise HTTPException(
            status_code=403,
            detail="Отказано в доступе...",
            headers={"WWW-Authenticate": "Bearer"},
        )


# загрузка ФАЙЛОВ пользователя
@app.get("/users/{id}/files", status_code=status.HTTP_200_OK)
async def download_docs(id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f'Пользователь с id {id} не загрузил файл...'
        )
    else:
        print(user.email.split('@', 0))
        return FileResponse(path=user.docs,
                            media_type='application/pdf',
                            filename=user.email.split('@', 0)[0] + '.pdf')


# получение формы для РЕГИСТРАЦИИ нового профиля
@app.get("/adminregister", status_code=status.HTTP_200_OK, response_class=HTMLResponse)
async def form_post(request: Request):
    return models.templates.TemplateResponse('adminregister.html', context={'request': request})

# отправка формы для РЕГИСТРАЦИИ профиля
@app.post("/adminregister", status_code=status.HTTP_201_CREATED, response_class=RedirectResponse)
async def form_post(
        request: Request,
        admfemail: str = Form(...),
        admfpasswd: str = Form(...),
        db: Session = Depends(get_db)
):
    isadmin = True
    new_admin = models.Admin(
        email=admfemail,
        hashed_password = auth.get_password_hash(admfpasswd)
    )
    access_token_expires = timedelta(
        minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token = auth.create_access_token(
        data={"sub": new_admin.email},
        isadmin=True,
        expires_delta=access_token_expires
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return models.templates.TemplateResponse(
        "adminalert.html",
        {"request": request,
         "detail": "Вы зарегистрированы как администратор!"
         }
    )

# вспомогательные функции
# полная ОЧИСТКА записей в базе данных users.db
@app.post("/cleardb/")
def clear_data(db: Session = Depends(get_db)):
    try:
        db.query(models.User).delete()
        db.commit()
        print("Data cleared successfully!")
    except Exception as e:
        db.rollback()
        print("Error occurred while clearing data:", str(e))
    finally:
        db.close()

# вывод ВСЕХ ТОКЕНОВ
@app.get("/print-tokens")
def print_tokens(db: Session = Depends(get_db)):
    tokens = db.query(models.Token).all()

    if tokens:
        print(f"Number of tokens: {len(tokens)}")
        for token in tokens:
            print(token)
        return tokens
    else:
        return('No tokens found in the database')

# обработка ИСКЛЮЧЕНИЙ HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    error_template = "error.html"
    error_code = exc.status_code
    error_detail = exc.detail
    prev_endpoint = request.headers.get("Referer", "/")     #для возвращения на предыдущую страницу
    return models.templates.TemplateResponse(error_template, {"request": request,
                                                              "error_code": error_code,
                                                              "error_detail": error_detail,
                                                              "prev_endpoint": prev_endpoint})
