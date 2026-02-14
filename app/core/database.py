from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. SQLite 데이터베이스 파일 경로 (프로젝트 폴더에 readgye.db 파일이 생깁니다)
SQLALCHEMY_DATABASE_URL = "sqlite:///./readgye.db"

# 2. 엔진 생성 (SQLite는 check_same_thread 옵션이 필요)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. 세션 생성기 (실제 DB와 대화하는 창구)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. 모델들이 상속받을 기본 클래스
Base = declarative_base()

# 5. DB 세션을 가져오는 의존성 함수 (FastAPI에서 사용)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()