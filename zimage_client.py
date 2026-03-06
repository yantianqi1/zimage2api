import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

logger = logging.getLogger(__name__)


class ZImageBrowser:
    """zimage.run 浏览器封装"""

    def __init__(
        self,
        state_file: str = "./data/storage-state.json",
        cookie_file: str = "./cookies.json",
        headless: bool = True,
        base_url: str = "https://zimage.run/zh",
    ):
        self.base_url = base_url
        self.state_file = state_file
        self.cookie_file = cookie_file
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self._initialized = False
        self._verification_required = False

    @property
    def initialized(self) -> bool:
        """浏览器是否已初始化。"""
        return self._initialized

    async def init(self, slow_mo: int = 0, timeout: int = 60000):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()

        # 浏览器启动参数 - 反检测
        launch_args = {
            "headless": self.headless,
            "slow_mo": slow_mo,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized",
            ]
        }

        self.browser = await self.playwright.chromium.launch(**launch_args)

        # 上下文选项 - 模拟真实用户
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "permissions": ["clipboard-read", "clipboard-write"],
        }

        if os.path.exists(self.state_file):
            context_options["storage_state"] = self.state_file
            logger.info("已加载 storage_state: %s", self.state_file)

        self.context = await self.browser.new_context(**context_options)

        # 注入反检测脚本
        await self.context.add_init_script("""
            // 覆盖 navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // 覆盖 permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ||
                parameters.name === 'clipboard-read' ||
                parameters.name === 'clipboard-write'
                    ? Promise.resolve({ state: 'granted' })
                    : originalQuery(parameters)
            );

            // 模拟插件
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // 覆盖 chrome 对象
            window.chrome = {
                runtime: {},
                app: {}
            };
        """)

        self.page = await self.context.new_page()
        self.page.set_default_timeout(timeout)

        self._initialized = True
        logger.info("浏览器初始化完成")

    async def open_homepage(self):
        """导航到目标网站"""
        logger.info("正在访问 %s", self.base_url)
        await self.page.goto(self.base_url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(1500)
        self._verification_required = await self._need_verification()
        if self._verification_required:
            logger.warning("检测到需要人机验证")

    async def _need_verification(self) -> bool:
        """检查是否需要验证"""
        try:
            # 检查 Cloudflare 验证框
            cf_selector = [
                '.cf-turnstile',
                '#cf-turnstile',
                '[data-sitekey]',
                'iframe[src*="challenges.cloudflare"]',
                '.verification-box',
                'text=人机验证',
                'text=请完成验证',
            ]

            for selector in cf_selector:
                if await self.page.locator(selector).count() > 0:
                    return True

            return False
        except Exception:
            return False

    async def check_ready(self) -> bool:
        """检查页面是否已到达可生成状态。"""
        if not self.page:
            return False

        if await self._need_verification():
            self._verification_required = True
            return False

        selectors = [
            'textarea[placeholder*="提示"]',
            'textarea[placeholder*="prompt"]',
            'input[placeholder*="描述"]',
            '[data-testid="prompt-input"]',
            'textarea',
        ]
        for selector in selectors:
            try:
                locator = self.page.locator(selector).first
                if await locator.count() > 0 and await locator.is_visible():
                    self._verification_required = False
                    return True
            except Exception:
                continue

        return False

    async def save_session(self):
        """保存会话"""
        if self.context:
            os.makedirs(os.path.dirname(self.state_file) or ".", exist_ok=True)
            await self.context.storage_state(path=self.state_file)
            logger.info("已保存 storage_state 到 %s", self.state_file)
            cookies = await self.context.cookies()
            with open(self.cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info("已同步 cookies 到 %s", self.cookie_file)

    async def generate_image(
        self,
        prompt: str,
        model: str = "turbo",
        size: str = "1024x1024",
        num_images: int = 1,
        negative_prompt: str = "",
        seed: Optional[int] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Dict[str, Any]:
        """
        生成图片

        Returns:
            {
                "success": bool,
                "images": [url1, url2, ...],
                "task_id": str,
                "error": str
            }
        """
        if not self._initialized:
            raise RuntimeError("浏览器未初始化")

        try:
            if not await self.check_ready():
                raise RuntimeError("会话未通过验证，无法执行生图。")

            await self._input_prompt(prompt)
            await self._select_model(model)
            await self._select_size(size)
            await self._select_quantity(num_images)
            await self._click_generate()
            return await self._wait_for_result(progress_callback)

        except Exception as exc:
            logger.error("生成图片失败: %s", exc)
            return {"success": False, "error": str(exc)}

    async def _input_prompt(self, prompt: str):
        """输入提示词"""
        # 尝试多种选择器
        selectors = [
            'textarea[placeholder*="提示"]',
            'textarea[placeholder*="prompt"]',
            'input[placeholder*="描述"]',
            '[data-testid="prompt-input"]',
            'textarea',
        ]

        for selector in selectors:
            try:
                await self.page.locator(selector).first.fill(prompt)
                logger.info(f"已输入提示词: {prompt[:50]}...")
                return
            except Exception:
                continue

        raise Exception("未找到提示词输入框")

    async def _select_model(self, model: str):
        """选择模型"""
        try:
            # 打开模型选择器
            model_button = self.page.locator('text=模型').first
            if await model_button.count() > 0:
                await model_button.click()
                await self.page.wait_for_timeout(500)

                # 选择具体模型
                model_option = self.page.locator(f'text={model}').first
                if await model_option.count() > 0:
                    await model_option.click()
                    logger.info("已选择模型: %s", model)
        except Exception as exc:
            logger.warning("选择模型失败: %s", exc)

    async def _select_size(self, size: str):
        """选择尺寸"""
        try:
            # 尺寸选择逻辑
            size_map = {
                "1024x1024": "1:1",
                "1024x1536": "2:3",
                "1536x1024": "3:2",
                "1920x1080": "16:9",
                "1080x1920": "9:16",
            }

            size_label = size_map.get(size, "1:1")

            # 点击尺寸选择
            size_button = self.page.locator(f'text={size_label}').first
            if await size_button.count() > 0:
                await size_button.click()
                logger.info("已选择尺寸: %s", size)
        except Exception as exc:
            logger.warning("选择尺寸失败: %s", exc)

    async def _select_quantity(self, num: int):
        """选择生成数量"""
        try:
            if num > 1:
                # 找到数量选择器
                qty_selector = self.page.locator('[data-testid="quantity"]').first
                if await qty_selector.count() > 0:
                    await qty_selector.click()
                    await self.page.locator(f'text={num}').first.click()
        except Exception as exc:
            logger.warning("选择数量失败: %s", exc)

    async def _click_generate(self):
        """点击生成按钮"""
        generate_selectors = [
            'button:has-text("生成")',
            'button:has-text("Generate")',
            '[data-testid="generate-button"]',
            'button[type="submit"]',
        ]

        for selector in generate_selectors:
            try:
                button = self.page.locator(selector).first
                if await button.count() > 0 and await button.is_visible():
                    await button.click()
                    logger.info("已点击生成按钮")
                    await self.page.wait_for_timeout(1000)
                    return
            except Exception:
                continue

        raise Exception("未找到生成按钮")

    async def _wait_for_result(
        self,
        progress_callback: Optional[Callable[[int], None]] = None,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """等待生成结果"""
        start_time = asyncio.get_running_loop().time()
        images = []

        while asyncio.get_running_loop().time() - start_time < timeout:
            # 检查是否完成 - 查找生成的图片
            try:
                # 查找结果图片
                image_selectors = [
                    'img[src*="files.zimage.run"]',
                    'img[alt*="生成"]',
                    '.generated-image img',
                    '[data-testid="result"] img',
                ]

                for selector in image_selectors:
                    elements = await self.page.locator(selector).all()
                    for el in elements:
                        src = await el.get_attribute("src")
                        if src and src not in images:
                            images.append(src)

                if len(images) > 0:
                    logger.info("生成完成，找到 %s 张图片", len(images))
                    return {
                        "success": True,
                        "images": images,
                        "task_id": f"task_{int(start_time)}"
                    }

                # 检查错误
                error_selectors = [
                    'text=生成失败',
                    'text=错误',
                    'text=请重试',
                ]
                for selector in error_selectors:
                    if await self.page.locator(selector).count() > 0:
                        error_text = await self.page.locator(selector).first.text_content()
                        return {"success": False, "error": error_text}

                # 更新进度
                if progress_callback:
                    elapsed = int(asyncio.get_running_loop().time() - start_time)
                    progress = min(int(elapsed / timeout * 100), 95)
                    progress_callback(progress)

            except Exception as exc:
                logger.debug("等待结果时出错: %s", exc)

            await self.page.wait_for_timeout(2000)

        return {"success": False, "error": "生成超时"}

    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.save_session()

        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self._initialized = False
        logger.info("浏览器已关闭")
