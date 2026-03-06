"""
配置文件
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API配置
    API_KEY: str = "your-secret-api-key"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # 浏览器配置
    HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 60000
    BROWSER_SLOW_MO: int = 0

    # 会话配置
    COOKIE_FILE: str = "./cookies.json"
    SESSION_REFRESH_INTERVAL: int = 1800  # 30分钟

    # 重试配置
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5

    # 日志
    LOG_LEVEL: str = "INFO"

    # ZImage网站配置
    ZIMAGE_URL: str = "https://zimage.run/zh"
    ZIMAGE_GENERATE_TIMEOUT: int = 120  # 生图超时时间(秒)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
