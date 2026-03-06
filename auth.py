"""API认证模块"""
from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """验证API密钥"""
    token = credentials.credentials
    api_key = request.app.state.settings.API_KEY

    if token != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API密钥",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token
