import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models.contract import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/contact", tags=["Contact"])


class ContactRequest(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=2000)


CONTACT_CATEGORY_LABELS: Dict[str, str] = {
    "service": "서비스 이용",
    "account": "계정 문제",
    "payment": "결제/환불",
    "bug": "오류 신고",
    "etc": "제안/기타",
}


def _send_contact_email(
    *,
    sender_email: str,
    recipient_email: str,
    subject: str,
    body: str,
):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port_raw = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    if not smtp_host or not smtp_user or not smtp_password:
        raise HTTPException(
            status_code=500,
            detail="메일 서버 설정이 누락되었습니다. 관리자에게 문의해 주세요.",
        )

    try:
        smtp_port = int(smtp_port_raw)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="SMTP_PORT 설정이 올바르지 않습니다.") from exc

    message = MIMEText(body, _charset="utf-8")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = recipient_email

    try:
        if smtp_use_tls:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_password)
                server.sendmail(sender_email, [recipient_email], message.as_string())
        else:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(sender_email, [recipient_email], message.as_string())
    except Exception as exc:
        print(f"[CONTACT ERROR] 메일 발송 실패: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=502,
            detail=f"문의 메일 발송에 실패했습니다: {exc}",
        ) from exc


@router.post("")
def submit_contact(
    payload: ContactRequest,
    current_user: User = Depends(get_current_user),
):
    support_email = os.getenv("SUPPORT_EMAIL_TO", "support@readgye.com")
    sender_email = os.getenv("SMTP_SENDER_EMAIL", os.getenv("SMTP_USER", ""))
    category_label = CONTACT_CATEGORY_LABELS.get(payload.category, payload.category)

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = f"[Readgye 문의] {payload.title}"
    body = (
        f"문의 유형: {category_label}\n"
        f"작성자: {current_user.name} ({current_user.email})\n"
        f"접수 시각: {timestamp}\n"
        f"\n"
        f"제목: {payload.title}\n"
        f"\n"
        f"내용:\n{payload.content}\n"
    )

    _send_contact_email(
        sender_email=sender_email,
        recipient_email=support_email,
        subject=subject,
        body=body,
    )
    return {"ok": True}
