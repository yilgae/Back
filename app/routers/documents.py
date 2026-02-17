from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.contract import Document, User, Clause, ClauseAnalysis
import uuid

# ★ 프론트엔드 요청 주소(/api/analyze)에 맞춤
router = APIRouter(
    prefix="/api/analyze", 
    tags=["Documents Management"],
)

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    특정 문서 및 관련 분석 데이터를 영구 삭제합니다.
    (본인이 올린 문서만 삭제 가능)
    """
    try:
        # UUID 형변환 시도 (유효하지 않은 ID가 올 경우 방어)
        try:
            target_uuid = uuid.UUID(document_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 문서 ID입니다.")

        # 1. 문서 찾기 (내 문서인지 확인)
        document = db.query(Document).filter(
            Document.id == target_uuid,
            Document.owner_id == current_user.id
        ).first()

        if not document:
            raise HTTPException(
                status_code=404, 
                detail="문서를 찾을 수 없거나 삭제 권한이 없습니다."
            )

        # 2. 연관된 데이터 삭제 (Cascade 삭제가 DB에 설정 안 되어 있을 경우를 대비해 수동 삭제)
        # (1) 해당 문서의 조항들(Clauses) 찾기
        clauses = db.query(Clause).filter(Clause.document_id == target_uuid).all()
        for clause in clauses:
            # (2) 조항별 분석(Analysis) 삭제
            db.query(ClauseAnalysis).filter(ClauseAnalysis.clause_id == clause.id).delete()
        
        # (3) 조항 삭제
        db.query(Clause).filter(Clause.document_id == target_uuid).delete()
        
        # (4) 문서(Document) 본체 삭제
        db.delete(document)
        
        db.commit()

        return {"status": "success", "message": "문서가 성공적으로 삭제되었습니다."}

    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 문서 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail="문서 삭제 중 오류가 발생했습니다.")