"""API认证模块"""
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

security = HTTPBearer()

# 从环境变量获取API密钥
API_KEY = os.getenv("API_KEY", "your-secret-api-key")


async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """验证API密钥"""
    token = credentials.credentials

    if token != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API密钥",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token
