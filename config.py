"""配置文件"""

from functools import lru_cache

from pydantic import ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API配置
    API_KEY: str = "your-secret-api-key"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # 浏览器配置
    HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 60000
    BROWSER_SLOW_MO: int = 0
    BROWSER_LOCALE: str = "zh-CN"
    BROWSER_TIMEZONE: str = "UTC"
    BROWSER_USER_AGENT: str = ""

    # 会话配置
    COOKIE_FILE: str = "./cookies.json"
    STATE_FILE: str = "./data/storage-state.json"
    SESSION_REFRESH_INTERVAL: int = 1800
    SESSION_TTL_CHECK_INTERVAL: int = 300
    HANDOFF_ENABLED: bool = True
    NOVNC_BASE_URL: str = "http://localhost:6080/vnc.html"
    SESSION_MODE: str = "headless"
    MAX_CONCURRENT_TASKS: int = 1

    # 重试配置
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5

    # 日志
    LOG_LEVEL: str = "INFO"

    # ZImage网站配置
    ZIMAGE_URL: str = "https://zimage.run/zh"
    ZIMAGE_GENERATE_TIMEOUT: int = 120


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
