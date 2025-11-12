from datetime import datetime
import logging
import os
import smtplib

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/mailserver-api/app.log'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mailserver Inbound API", version="1.0.0")

API_KEY = os.getenv("API_KEY")
LMTP_HOST = os.getenv("LMTP_HOST", "dovecot")
LMTP_PORT = int(os.getenv("LMTP_PORT", "2525"))


class InboundEmail(BaseModel):
    from_addr: str = Field(alias="from")
    to: EmailStr
    subject: str
    raw: str
    timestamp: str


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/v1/inbound-mail")
async def receive_inbound_mail(email: InboundEmail, x_api_key: str = Header(None)):
    if not x_api_key or not API_KEY or x_api_key != API_KEY:
        logger.warning("Invalid API key access attempt")
        raise HTTPException(status_code=401, detail="Invalid API Key")

    logger.info(
        "Inbound email received from %s to %s subject=%s",
        email.from_addr,
        email.to,
        email.subject,
    )

    try:
        with smtplib.LMTP(LMTP_HOST, LMTP_PORT, timeout=30) as lmtp:
            # LMTP expects a per-recipient response, but we only send to one address
            lmtp.sendmail(email.from_addr, [email.to], email.raw.encode("utf-8"))
        logger.info("LMTP delivery succeeded for %s", email.to)
        return {"status": "success", "message": "Email delivered to LMTP", "recipient": email.to}
    except smtplib.SMTPException as exc:
        logger.error("LMTP delivery error: %s", exc)
        raise HTTPException(status_code=500, detail=f"LMTP error: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc
