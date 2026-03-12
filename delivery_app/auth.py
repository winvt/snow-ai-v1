"""Authentication helpers for LINE and app sessions."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
import requests


@dataclass
class LineProfile:
    line_user_id: str
    display_name: str
    picture_url: Optional[str]


class SessionManager:
    """Issue and verify signed session cookies."""

    def __init__(self, secret: str, salt: str = "delivery-session"):
        self.serializer = URLSafeTimedSerializer(secret_key=secret, salt=salt)

    def dumps(self, line_user_id: str) -> str:
        return self.serializer.dumps({"line_user_id": line_user_id})

    def loads(self, token: str, max_age: int) -> str:
        try:
            payload = self.serializer.loads(token, max_age=max_age)
        except SignatureExpired as exc:
            raise ValueError("session expired") from exc
        except BadSignature as exc:
            raise ValueError("invalid session") from exc
        line_user_id = payload.get("line_user_id")
        if not line_user_id:
            raise ValueError("invalid session")
        return line_user_id


class LineVerifier:
    """Verify LINE LIFF ID tokens using LINE's official endpoint."""

    verify_url = "https://api.line.me/oauth2/v2.1/verify"

    def __init__(self, channel_id: str):
        self.channel_id = channel_id

    def verify_id_token(self, id_token: str) -> LineProfile:
        if not self.channel_id:
            raise ValueError("LINE_CHANNEL_ID is not configured")
        response = requests.post(
            self.verify_url,
            data={"id_token": id_token, "client_id": self.channel_id},
            timeout=15,
        )
        if response.status_code != 200:
            raise ValueError("LINE token verification failed")
        payload = response.json()
        subject = payload.get("sub")
        name = payload.get("name") or "LINE User"
        if not subject:
            raise ValueError("LINE token verification returned no subject")
        return LineProfile(
            line_user_id=subject,
            display_name=name,
            picture_url=payload.get("picture"),
        )


def hash_admin_password(password: str) -> str:
    """Allow constant-time comparison without storing plaintext in memory multiple times."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

