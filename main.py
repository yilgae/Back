import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import fitz  # PyMuPDF (PDF 처리용)
from openai import OpenAI
from dotenv import load_dotenv
import json

# 1. .env 파일에서 API 키 불러오기
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 생성
client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()

# CORS 설정 (React Native 통신용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- [DTO: 데이터 전송 모델] ---
class ClauseAnalysis(BaseModel):
    clause_number: str
    title: str
    risk_level: str  # HIGH, MEDIUM, LOW
    summary: str
    suggestion: str

class AnalysisResponse(BaseModel):
    filename: str
    total_clauses: int
    high_risk_count: int
    clauses: list[ClauseAnalysis]

# --- [핵심 기능 1: PDF에서 텍스트 추출] ---
def extract_text_from_pdf(file_content: bytes) -> str:
    """PDF 파일의 바이너리 데이터를 받아서 텍스트만 뽑아냅니다."""
    try:
        # 메모리에 있는 파일 내용을 PyMuPDF로 엽니다
        doc = fitz.open(stream=file_content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"PDF 추출 에러: {e}")
        return ""

# --- [핵심 기능 2: OpenAI에게 분석 요청] ---
def analyze_with_gpt(contract_text: str) -> dict:
    """
    GPT 호출을 시도하고, 돈이 없거나 에러가 나면 '가짜 결과'를 반환합니다.
    """
    # --- [비상용 가짜 데이터] ---
    dummy_response = {
        "clauses": [
            {
                "clause_number": "제5조",
                "title": "손해배상(테스트)",
                "risk_level": "HIGH",
                "summary": "API 크레딧 부족으로 인해 표시되는 테스트용 데이터입니다.",
                "suggestion": "OpenAI Billing 페이지에서 크레딧을 충전하면 실제 분석이 됩니다."
            },
            {
                "clause_number": "제12조",
                "title": "계약 해지",
                "risk_level": "LOW",
                "summary": "이 내용은 안전합니다.",
                "suggestion": "수정할 필요가 없습니다."
            }
        ]
    }

    try:
        # 프롬프트 설계
        system_prompt = """
        너는 전문 변호사야. 사용자가 계약서 텍스트를 주면, 
        독소 조항이나 불리한 내용을 찾아서 분석해줘.
        JSON 포맷으로만 응답해.
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # gpt-4o보다 훨씬 싸서 테스트용으로 추천
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": contract_text[:10000]} # 글자수 좀 줄임
            ],
            # response_format={"type": "json_object"}, # 3.5-turbo 구버전은 이거 빼야 할 수도 있음
        )
        
        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        print(f"⚠️ AI 호출 실패 (더미 데이터 반환): {e}")
        # 에러가 나면 프로그램이 죽는 게 아니라, 가짜 데이터를 리턴해서 프론트엔드가 안 멈추게 함
        return dummy_response

# --- [API 엔드포인트] ---

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_contract(file: UploadFile = File(...)):
    print(f"\n[파일 업로드 됨] 파일명: {file.filename}")
    
    # 1. 파일 읽기
    content = await file.read()
    
    # 2. 텍스트 추출
    extracted_text = extract_text_from_pdf(content)
    
    # --- [여기가 추가된 부분입니다] ---
    print("\n" + "="*50)
    if extracted_text:
        print(f"📜 PDF 텍스트 추출 성공! (총 {len(extracted_text)} 글자)")
        print("-" * 20 + " [내용 미리보기] " + "-" * 20)
        print(extracted_text[:2000])  # 앞부분 2000자만 출력 (다 보고 싶으면 [:2000] 지우세요)
        print("\n" + "-" * 50)
        if len(extracted_text) > 2000:
            print("... (내용이 너무 길어서 생략됨) ...")
    else:
        print("⚠️ 경고: 텍스트가 추출되지 않았습니다! (이미지 파일이거나 암호화됨)")
    print("="*50 + "\n")
    # -------------------------------

    if not extracted_text:
        raise HTTPException(status_code=400, detail="PDF에서 텍스트를 읽을 수 없습니다.")
    
    # 3. AI 분석 요청 (가짜 데이터 or 진짜 AI)
    ai_result = analyze_with_gpt(extracted_text)
    
    # 4. 결과 가공
    analyzed_clauses = []
    for item in ai_result.get("clauses", []):
        analyzed_clauses.append(ClauseAnalysis(**item))
        
    high_risk_count = len([c for c in analyzed_clauses if c.risk_level == "HIGH"])

    return AnalysisResponse(
        filename=file.filename,
        total_clauses=len(analyzed_clauses),
        high_risk_count=high_risk_count,
        clauses=analyzed_clauses,
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)