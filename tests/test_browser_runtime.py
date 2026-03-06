from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Settings
from zimage_client import ZImageBrowser


def test_dockerfile_installs_cjk_fonts():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "fonts-noto-cjk" in dockerfile
    assert "fonts-wqy-zenhei" in dockerfile


def test_context_options_do_not_force_mac_user_agent_by_default(tmp_path):
    browser = ZImageBrowser(
        state_file=str(tmp_path / "state.json"),
        cookie_file=str(tmp_path / "cookies.json"),
    )

    options = browser.build_context_options(
        Settings(
            BROWSER_LOCALE="zh-CN",
            BROWSER_TIMEZONE="UTC",
        )
    )

    assert options["locale"] == "zh-CN"
    assert options["timezone_id"] == "UTC"
    assert "user_agent" not in options


def test_launch_args_do_not_include_suspicious_flags():
    browser = ZImageBrowser()
    args = browser.build_launch_options()["args"]

    assert "--disable-web-security" not in args
    assert "--disable-site-isolation-trials" not in args
    assert "--disable-gpu" not in args
