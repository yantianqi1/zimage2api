"""会话初始化脚本 - 首次运行时使用"""
import asyncio
import sys
from zimage_client import ZImageBrowser


async def main():
    print("=" * 50)
    print("ZImage 会话初始化工具")
    print("=" * 50)
    print()
    print("此脚本将打开浏览器并访问 zimage.run")
    print("请完成人机验证后，按回车保存会话")
    print()

    # 使用非headless模式以便人工验证
    browser = ZImageBrowser(
        cookie_file="./cookies.json",
        headless=False  # 必须可见才能完成验证
    )

    try:
        print("正在启动浏览器...")
        await browser.init(slow_mo=100)

        print()
        print("浏览器已打开，请完成以下操作：")
        print("1. 如果看到人机验证，请手动完成")
        print("2. 确保页面正常加载")
        print("3. 按回车键保存会话")
        print()

        # 等待用户按回车
        if sys.platform == "win32":
            input("按回车键保存会话...")
        else:
            input("按回车键保存会话...")

        await browser.save_session()
        print()
        print("✓ 会话已保存到 cookies.json")
        print("✓ 现在可以使用 headless 模式启动 API 服务")

    except Exception as e:
        print(f"\n✗ 错误: {e}")
    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
