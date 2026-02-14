# app/routers/upload.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.pdf_parser import extract_text_from_pdf
from app.services.analyzer import analyze_contract_text
from app.models import contract, schemas
from app.routers.auth import get_current_user # 로그인한 사용자만 업로드 가능하게

router = APIRouter(prefix="/api/analyze", tags=["Analyze"])

@router.post("", response_model=schemas.DocumentResponse) # /api/analyze 로 요청
async def analyze_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: contract.User = Depends(get_current_user)
):
    print(f"📂 파일 수신: {file.filename}")

    # 1. 파일 읽기
    content = await file.read()
    
    # 2. 텍스트 추출 (서비스 호출)
    text = extract_text_from_pdf(content)
    if not text:
        raise HTTPException(status_code=400, detail="PDF에서 텍스트를 읽을 수 없습니다.")

    # 3. AI 분석 (서비스 호출)
    ai_result = analyze_contract_text(text)
    
    # 4. DB에 저장 (Document -> Clause -> Analysis 순서로)
    
    # (1) 문서 저장
    new_doc = contract.Document(
        filename=file.filename,
        owner_id=current_user.id,
        status="done"
    )
    db.add(new_doc)
    db.flush() # ID 생성을 위해 flush
    
    analyzed_clauses = []
    
    # (2) 조항 및 분석 결과 저장
    for item in ai_result.get("clauses", []):
        # 조항 저장
        new_clause = contract.Clause(
            document_id=new_doc.id,
            clause_number=item.get("clause_number"),
            title=item.get("title"),
            body="" # 원문은 일단 비워둠 (매칭 로직 복잡함 생략)
        )
        db.add(new_clause)
        db.flush()
        
        # 분석 결과 저장
        new_analysis = contract.ClauseAnalysis(
            clause_id=new_clause.id,
            risk_level=item.get("risk_level"),
            summary=item.get("summary"),
            suggestion=item.get("suggestion")
        )
        db.add(new_analysis)
        
        # 반환용 데이터 만들기 (DB 객체 -> Pydantic 변환이 자동으론 힘들 수 있어서 수동 매핑)
        # (하지만 response_model 설정을 믿고 진행)

    db.commit()
    db.refresh(new_doc)
    
    # 5. 결과 반환 (risk_count 계산 필요)
    risk_count = 0
    for clause in new_doc.clauses:
        if clause.analysis and clause.analysis.risk_level == "HIGH":
            risk_count += 1
            
    # Pydantic 스키마에 맞춰서 리턴
    return schemas.DocumentResponse(
        id=str(new_doc.id),
        filename=new_doc.filename,
        status=new_doc.status,
        created_at=new_doc.created_at,
        risk_count=risk_count
    )