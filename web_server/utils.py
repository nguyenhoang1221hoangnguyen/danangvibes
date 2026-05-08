from __future__ import annotations

import hmac

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from web_server.config import settings

security = HTTPBasic(auto_error=False)


def verify_admin_token(
    authorization: str | None = Header(default=None),
    x_admin_token: str | None = Header(default=None),
    credentials: HTTPBasicCredentials | None = Depends(security),
) -> None:
    if not settings.admin_token:
        raise HTTPException(status_code=401, detail="DANANGVIBES_ADMIN_TOKEN is not configured")
    token = x_admin_token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    if credentials:
        token = credentials.password
    if not hmac.compare_digest(token or "", settings.admin_token):
        raise HTTPException(status_code=401, detail="Invalid admin token", headers={"WWW-Authenticate": "Basic"})
