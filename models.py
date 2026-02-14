# Back/models.py

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, CHAR
from database import Base
import uuid
import datetime

# SQLite에서 UUID를 저장하기 위한 호환성 설정 (복잡해 보이면 무시하셔도 됩니다)
class GUID(TypeDecorator):
    impl = CHAR
    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(CHAR(36))
    def process_bind_param(self, value, dialect):
        if value is None: return value
        return str(value)
    def process_result_value(self, value, dialect):
        if value is None: return value
        return uuid.UUID(value)

# 1. 문서 테이블 (사용자가 업로드한 파일)
class Document(Base):
    __tablename__ = "documents"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    filename = Column(String, index=True) # 파일명 추가
    status = Column(String, default="uploaded") # uploaded, analyzing, done, failed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 관계 설정 (1:N)
    clauses = relationship("Clause", back_populates="document")

# 2. 조항 테이블 (제1조, 제2조...)
class Clause(Base):
    __tablename__ = "clauses"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID(), ForeignKey("documents.id"))
    clause_number = Column(String) # 제1조
    title = Column(String)         # 목적
    body = Column(Text)            # 본문 내용
    
    # 관계 설정
    document = relationship("Document", back_populates="clauses")
    analysis = relationship("ClauseAnalysis", uselist=False, back_populates="clause")

# 3. 분석 결과 테이블 (AI가 분석한 내용)
class ClauseAnalysis(Base):
    __tablename__ = "clause_analysis"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    clause_id = Column(GUID(), ForeignKey("clauses.id"))
    
    risk_level = Column(String) # HIGH, MEDIUM, LOW
    summary = Column(Text)      # 위험 요약
    suggestion = Column(Text)   # 수정 제안
    
    # JSON 형태로 저장 (태그 등)
    tags = Column(JSON, default=[]) 
    
    clause = relationship("Clause", back_populates="analysis")