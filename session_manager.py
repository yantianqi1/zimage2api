"""会话管理器。"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

from config import Settings
from models import SessionState, SessionStatusResponse
from zimage_client import ZImageBrowser

logger = logging.getLogger(__name__)


class SessionNotReadyError(RuntimeError):
    """会话不可用于任务执行。"""

    def __init__(self, status: str, message: str, code: str = "session_required"):
        super().__init__(message)
        self.session_status = status
        self.code = code


class SessionManager:
    """管理浏览器会话生命周期与人工接管状态。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.browser: Optional[ZImageBrowser] = None
        self.status = SessionState.UNINITIALIZED
        self.handoff_url: Optional[str] = None
        self.message: Optional[str] = None
        self._lock = asyncio.Lock()

    async def startup(self):
        """启动时加载会话。"""
        if os.path.exists(self.settings.STATE_FILE):
            await self.refresh()
            return

        self.status = SessionState.NEEDS_HUMAN
        self.message = "未找到可复用的会话状态，请先进行服务器端人工接管。"

    async def shutdown(self):
        """关闭浏览器。"""
        await self._close_browser()

    async def get_status(self) -> SessionStatusResponse:
        """获取当前会话状态。"""
        return SessionStatusResponse(
            status=self.status,
            ready=self.status == SessionState.READY,
            handoff_url=self.handoff_url,
            message=self.message,
        )

    async def require_ready(self):
        """确保当前会话可用于任务执行。"""
        if self.status != SessionState.READY:
            raise SessionNotReadyError(
                status=self.status.value,
                message=self.message or "会话未就绪，请先完成人工接管。",
            )

    async def start_handoff(self) -> SessionStatusResponse:
        """进入人工接管模式。"""
        async with self._lock:
            await self._launch_browser(headless=False)
            self.status = SessionState.HANDOFF_ACTIVE
            self.handoff_url = self.settings.NOVNC_BASE_URL
            self.message = "请通过服务器端 noVNC 页面完成验证。"
            await self.browser.open_homepage()
            return await self.get_status()

    async def complete_handoff(self) -> SessionStatusResponse:
        """完成接管并保存状态。"""
        async with self._lock:
            if not self.browser:
                self.status = SessionState.NEEDS_HUMAN
                self.message = "当前没有活动中的接管会话。"
                return await self.get_status()

            ready = await self.browser.check_ready()
            if not ready:
                self.status = SessionState.HANDOFF_ACTIVE
                self.message = "验证尚未完成，请继续在 noVNC 页面操作。"
                return await self.get_status()

            await self.browser.save_session()
            await self._close_browser()
            await self._launch_browser(headless=self.settings.HEADLESS)
            self.status = SessionState.READY
            self.handoff_url = None
            self.message = "会话已就绪。"
            return await self.get_status()

    async def refresh(self) -> SessionStatusResponse:
        """刷新当前会话。"""
        async with self._lock:
            try:
                await self._launch_browser(headless=self.settings.HEADLESS)
                await self.browser.open_homepage()
                ready = await self.browser.check_ready()
                if ready:
                    await self.browser.save_session()
                    self.status = SessionState.READY
                    self.handoff_url = None
                    self.message = "会话可用。"
                else:
                    self.status = SessionState.NEEDS_HUMAN
                    self.message = "会话失效，需要人工接管。"
                return await self.get_status()
            except Exception as exc:
                logger.exception("刷新会话失败")
                self.status = SessionState.ERROR
                self.message = f"刷新会话失败: {exc}"
                return await self.get_status()

    async def generate_image(self, **kwargs: Any) -> dict:
        """调用浏览器执行生图。"""
        async with self._lock:
            await self.require_ready()
            return await self.browser.generate_image(**kwargs)

    async def _launch_browser(self, headless: bool):
        if self.browser and self.browser.headless == headless and self.browser.initialized:
            return

        await self._close_browser()
        self.browser = ZImageBrowser(
            state_file=self.settings.STATE_FILE,
            cookie_file=self.settings.COOKIE_FILE,
            headless=headless,
            base_url=self.settings.ZIMAGE_URL,
        )
        await self.browser.init(
            slow_mo=self.settings.BROWSER_SLOW_MO,
            timeout=self.settings.BROWSER_TIMEOUT,
        )

    async def _close_browser(self):
        if self.browser:
            await self.browser.close()
        self.browser = None
