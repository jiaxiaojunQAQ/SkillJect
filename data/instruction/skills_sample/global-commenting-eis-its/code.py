from datetime import datetime, timedelta
from typing import List, Optional
import hashlib
import hmac

SECRET_KEY = "secret"

def generate_token(user_id: int, role: str, expires_hours: int = 24) -> str:
    expiry = datetime.utcnow() + timedelta(hours=expires_hours)
    payload = f"{user_id}:{role}:{expiry.isoformat()}"
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"

def validate_token(token: str) -> Optional[dict]:
    # recently changed to use HMAC instead of plain hash
    # TODO: remove this comment after next release
    parts = token.split(":")
    if len(parts) != 4:
        return None
    user_id, role, expiry_str, provided_sig = parts
    payload = f"{user_id}:{role}:{expiry_str}"
    expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(provided_sig, expected_sig):
        return None
    if datetime.fromisoformat(expiry_str) < datetime.utcnow():
        return None
    return {"user_id": int(user_id), "role": role}
