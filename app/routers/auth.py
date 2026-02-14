# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import os

# ★ 바뀐 경로들로 import
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, SECRET_KEY, ALGORITHM
from app.models import contract, schemas # models 폴더 안의 파일들

router = APIRouter(prefix="/api/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ★ get_current_user 함수도 여기서 정의하거나 core/security.py 로 빼도 됨 (일단 여기 둠)
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명이 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None: raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(contract.User).filter(contract.User.email == email).first()
    if user is None: raise credentials_exception
    return user

# ... (signup, login, me 함수들은 기존 auth.py 로직 그대로 쓰되, 
#      models.User 대신 contract.User, 
#      UserCreate 대신 schemas.UserCreate 등을 사용하도록 수정) ...