# app/routers/upload.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.core.database import get_db
from app.services.pdf_parser import extract_content_from_pdf
from app.services.analyzer import analyze_contract
from app.models import contract, schemas
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/analyze", tags=["Analyze"])

@router.post("", response_model=schemas.DocumentResponse)
async def analyze_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: contract.User = Depends(get_current_user)
):
    content_bytes = await file.read()
    print(f"\n[DEBUG 1] 파일 읽기 완료: {file.filename} ({len(content_bytes)} bytes)")
    
    parsed_data = extract_content_from_pdf(content_bytes)
    print(f"[DEBUG 2] PDF 추출 타입: {parsed_data['type']}")
    
    # AI 분석 전 데이터 확인
    ai_result = analyze_contract(parsed_data)
    print(f"[DEBUG 3] AI 분석 결과 수신: {ai_result}") # <--- 여기가 []인지 확인!
    
    # 4. DB 저장 프로세스
    # (1) 문서 레코드 생성
    new_doc = contract.Document(
        id=uuid.uuid4(),
        filename=file.filename,
        owner_id=current_user.id,
        status="done"
    )
    db.add(new_doc)
    db.flush() 

    # (2) 조항 및 분석 결과 저장 루프
    clauses_data = ai_result.get("clauses", [])
    risk_count = 0

    for item in clauses_data:
        # 조항 저장
        new_clause = contract.Clause(
            id=uuid.uuid4(),
            document_id=new_doc.id,
            clause_number=item.get("clause_number", "미분류"),
            title=item.get("title", "제목 없음"),
            body="" # 원문 매칭은 추후 고도화 과제
        )
        db.add(new_clause)
        db.flush()
        
        # 분석 상세 저장
        risk_level = item.get("risk_level", "LOW")
        if risk_level == "HIGH":
            risk_count += 1
            
        new_analysis = contract.ClauseAnalysis(
            id=uuid.uuid4(),
            clause_id=new_clause.id,
            risk_level=risk_level,
            summary=item.get("summary", ""),
            suggestion=item.get("suggestion", "")
        )
        db.add(new_analysis)

    db.commit()
    db.refresh(new_doc)
    
    # 5. 최종 응답 반환 (UUID 객체를 schemas.py가 잘 처리하도록 설정 확인 필요)
    return schemas.DocumentResponse(
        id=new_doc.id,
        filename=new_doc.filename,
        status=new_doc.status,
        created_at=new_doc.created_at,
        risk_count=risk_count
    )

# 상세 결과 조회를 위한 추가 엔드포인트 (추천)
@router.get("/{document_id}/result")
def get_analysis_detail(document_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.query(contract.Document).filter(contract.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
        
    results = []
    for clause in doc.clauses:
        results.append({
            "clause_number": clause.clause_number,
            "title": clause.title,
            "risk_level": clause.analysis.risk_level if clause.analysis else "UNKNOWN",
            "summary": clause.analysis.summary if clause.analysis else "",
            "suggestion": clause.analysis.suggestion if clause.analysis else ""
        })
    
    return {"filename": doc.filename, "analysis": results}