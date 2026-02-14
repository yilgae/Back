# app/services/analyzer.py

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def analyze_contract_text(text: str) -> dict:
    """
    GPT에게 계약서 텍스트를 보내고 JSON 결과를 받습니다.
    (API 키가 없거나 에러가 나면 더미 데이터를 반환합니다)
    """
    
    # --- [비상용 가짜 데이터] ---
    dummy_response = {
        "clauses": [
            {
                "clause_number": "제5조",
                "title": "손해배상(테스트)",
                "risk_level": "HIGH",
                "summary": "서버 연결 성공! 다만 API 크레딧 문제로 테스트 데이터가 표시됩니다.",
                "suggestion": "OpenAI 결제 후 진짜 분석이 가능합니다."
            },
            {
                "clause_number": "제12조",
                "title": "계약 해지",
                "risk_level": "LOW",
                "summary": "이 조항은 안전합니다.",
                "suggestion": "수정할 필요가 없습니다."
            }
        ]
    }

    try:
        system_prompt = """
        너는 전문 변호사야. 계약서를 분석해서 독소 조항을 찾아줘.
        반드시 아래 JSON 포맷으로만 응답해:
        {
            "clauses": [
                { "clause_number": "...", "title": "...", "risk_level": "HIGH/MEDIUM/LOW", "summary": "...", "suggestion": "..." }
            ]
        }
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini", # 가성비 모델
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:15000]}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        print(f"⚠️ AI 분석 실패 (더미 데이터 사용): {e}")
        return dummy_response