# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.routers import auth, upload # upload 등 다른 라우터도 완성되면 import

# DB 테이블 자동 생성
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router)
# app.include_router(upload.router) # 완성되면 주석 해제

@app.get("/")
def read_root():
    return {"Hello": "ReadGye Refactored Backend!"}