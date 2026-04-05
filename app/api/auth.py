from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.services.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.user import DBUser

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class UserResponse(BaseModel):
    id: int
    username: str
    role: str


class NewUser(BaseModel):
    username: str
    password: str
    role: str


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> DBUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token 無效或已過期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(DBUser).where(DBUser.username == username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user


async def get_admin_user(current_user: DBUser = Depends(get_current_user)) -> DBUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="權限不足")
    return current_user


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DBUser).where(DBUser.username == form_data.username)
    )
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}


@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    admin: DBUser = Depends(get_admin_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(DBUser))
    return result.scalars().all()


@router.post("/users")
async def create_user(
    new_user: NewUser,
    admin: DBUser = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DBUser).where(DBUser.username == new_user.username)
    )
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="帳號已存在")

    db_user = DBUser(
        username=new_user.username,
        hashed_password=get_password_hash(new_user.password),
        role=new_user.role,
    )
    db.add(db_user)
    await db.commit()
    return {"msg": "帳號建立成功"}
