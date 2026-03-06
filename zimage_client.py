"""浏览器自动化核心模块"""
import asyncio
import json
import os
from typing import Optional, List, Dict, Any, Callable
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import logging

logger = logging.getLogger(__name__)


class ZImageBrowser:
    """zimage.run 浏览器封装"""

    BASE_URL = "https://zimage.run/zh"

    def __init__(self, cookie_file: str = "./cookies.json", headless: bool = True):
        self.cookie_file = cookie_file
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self._initialized = False

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

        # 加载已有cookie
        if os.path.exists(self.cookie_file):
            with open(self.cookie_file, "r") as f:
                cookies = json.load(f)
                context_options["storage_state"] = {"cookies": cookies}
                logger.info(f"已加载 {len(cookies)} 个cookie")

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

        await self._navigate_to_site()
        self._initialized = True
        logger.info("浏览器初始化完成")

    async def _navigate_to_site(self):
        """导航到目标网站"""
        logger.info(f"正在访问 {self.BASE_URL}")
        await self.page.goto(self.BASE_URL, wait_until="networkidle")

        # 等待页面加载完成
        await asyncio.sleep(2)

        # 检查是否需要验证
        if await self._need_verification():
            logger.warning("检测到需要人机验证")
            await self._handle_verification()

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
        except:
            return False

    async def _handle_verification(self):
        """处理验证"""
        logger.info("等待人工完成验证...")
        logger.info("请在浏览器中完成人机验证，完成后按回车继续")

        if not self.headless:
            # 非headless模式，等待用户操作
            await asyncio.sleep(30)  # 给用户30秒时间
        else:
            # headless模式需要特殊处理
            await asyncio.sleep(10)

    async def save_session(self):
        """保存会话"""
        if self.context:
            cookies = await self.context.cookies()
            with open(self.cookie_file, "w") as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"已保存 {len(cookies)} 个cookie")

    async def generate_image(
        self,
        prompt: str,
        model: str = "turbo",
        size: str = "1024x1024",
        num_images: int = 1,
        negative_prompt: str = "",
        seed: Optional[int] = None,
        progress_callback: Optional[Callable[[int], None]] = None
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
            # 1. 找到输入框并输入提示词
            await self._input_prompt(prompt)

            # 2. 选择模型
            await self._select_model(model)

            # 3. 选择尺寸
            await self._select_size(size)

            # 4. 选择数量
            await self._select_quantity(num_images)

            # 5. 点击生成按钮
            await self._click_generate()

            # 6. 等待结果
            result = await self._wait_for_result(progress_callback)

            return result

        except Exception as e:
            logger.error(f"生成图片失败: {e}")
            return {"success": False, "error": str(e)}

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
            except:
                continue

        raise Exception("未找到提示词输入框")

    async def _select_model(self, model: str):
        """选择模型"""
        try:
            # 打开模型选择器
            model_button = await self.page.locator('text=模型').first
            if await model_button.count() > 0:
                await model_button.click()
                await asyncio.sleep(0.5)

                # 选择具体模型
                model_option = await self.page.locator(f'text={model}').first
                if await model_option.count() > 0:
                    await model_option.click()
                    logger.info(f"已选择模型: {model}")
        except Exception as e:
            logger.warning(f"选择模型失败: {e}")

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
            size_button = await self.page.locator(f'text={size_label}').first
            if await size_button.count() > 0:
                await size_button.click()
                logger.info(f"已选择尺寸: {size}")
        except Exception as e:
            logger.warning(f"选择尺寸失败: {e}")

    async def _select_quantity(self, num: int):
        """选择生成数量"""
        try:
            if num > 1:
                # 找到数量选择器
                qty_selector = await self.page.locator('[data-testid="quantity"]').first
                if await qty_selector.count() > 0:
                    await qty_selector.click()
                    await self.page.locator(f'text={num}').first.click()
        except Exception as e:
            logger.warning(f"选择数量失败: {e}")

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
                    await asyncio.sleep(1)
                    return
            except:
                continue

        raise Exception("未找到生成按钮")

    async def _wait_for_result(
        self,
        progress_callback: Optional[Callable[[int], None]] = None,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """等待生成结果"""
        start_time = asyncio.get_event_loop().time()
        images = []

        while asyncio.get_event_loop().time() - start_time < timeout:
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
                    logger.info(f"生成完成，找到 {len(images)} 张图片")
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
                    elapsed = int(asyncio.get_event_loop().time() - start_time)
                    progress = min(int(elapsed / timeout * 100), 95)
                    progress_callback(progress)

            except Exception as e:
                logger.debug(f"等待结果时出错: {e}")

            await asyncio.sleep(2)

        return {"success": False, "error": "生成超时"}

    async def close(self):
        """关闭浏览器"""
        await self.save_session()

        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self._initialized = False
        logger.info("浏览器已关闭")
