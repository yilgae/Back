# app/services/analyzer.py
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_contract(data: dict) -> dict:
    """
    텍스트 또는 이미지 데이터를 받아 GPT-4o에게 분석을 요청합니다.
    """
    system_prompt = """
    너는 전문 변호사야. 제공된 계약서(텍스트 또는 이미지)를 분석해서 독소 조항을 찾아줘.
    반드시 아래 JSON 포맷으로만 응답해:
    {
        "clauses": [
            { "clause_number": "제N조", "title": "조항 제목", "risk_level": "HIGH/MEDIUM/LOW", "summary": "위험 요약", "suggestion": "수정 제안" }
        ]
    }
    """

    content = [{"type": "text", "text": "이 계약서를 분석해서 독소 조항을 찾아줘."}]

    if data["type"] == "text":
        content[0]["text"] += f"\n\n계약서 내용:\n{data['content'][:15000]}"
    else:
        # 이미지 분석 (첫 3페이지만 샘플링하여 비용/속도 최적화)
        for img_base64 in data["content"][:3]:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_base64}"}
            })

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Vision 지원 및 가성비 모델
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ 분석 에러: {e}")
        return {"clauses": []} # 실패 시 빈 리스트 반환