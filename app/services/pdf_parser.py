# app/services/pdf_parser.py

import fitz # PyMuPDF

def extract_text_from_pdf(file_content: bytes) -> str:
    """PDF 파일의 바이너리 데이터를 받아서 텍스트만 뽑아냅니다."""
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"PDF 추출 에러: {e}")
        return ""