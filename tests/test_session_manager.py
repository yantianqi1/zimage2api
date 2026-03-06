import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Settings
from models import SessionState
from session_manager import SessionManager


class FakeBrowser:
    instances = []
    ready = True

    def __init__(self, state_file, cookie_file, headless, base_url):
        self.state_file = state_file
        self.cookie_file = cookie_file
        self.headless = headless
        self.base_url = base_url
        self.initialized = False
        self.opened = False
        self.saved = False
        self.closed = False
        FakeBrowser.instances.append(self)

    async def init(self, slow_mo=0, timeout=60000):
        self.initialized = True

    async def open_homepage(self):
        self.opened = True

    async def check_ready(self):
        return self.ready

    async def save_session(self):
        self.saved = True

    async def close(self):
        self.closed = True


def build_settings(tmp_path):
    return Settings(
        API_KEY="test-secret",
        STATE_FILE=str(tmp_path / "storage-state.json"),
        COOKIE_FILE=str(tmp_path / "cookies.json"),
        NOVNC_BASE_URL="http://novnc.local/?token=abc",
        HEADLESS=True,
    )


def test_startup_without_state_file_requires_handoff(tmp_path):
    settings = build_settings(tmp_path)
    manager = SessionManager(settings)

    asyncio.run(manager.startup())

    status = asyncio.run(manager.get_status())
    assert status.status == SessionState.NEEDS_HUMAN
    assert status.ready is False


def test_startup_with_state_file_refreshes_to_ready(tmp_path, monkeypatch):
    settings = build_settings(tmp_path)
    Path(settings.STATE_FILE).write_text("{}", encoding="utf-8")
    FakeBrowser.instances = []
    FakeBrowser.ready = True
    monkeypatch.setattr("session_manager.ZImageBrowser", FakeBrowser)
    manager = SessionManager(settings)

    asyncio.run(manager.startup())

    status = asyncio.run(manager.get_status())
    assert status.status == SessionState.READY
    assert FakeBrowser.instances[-1].saved is True


def test_complete_handoff_relaunches_headless_browser(tmp_path, monkeypatch):
    settings = build_settings(tmp_path)
    FakeBrowser.instances = []
    FakeBrowser.ready = True
    monkeypatch.setattr("session_manager.ZImageBrowser", FakeBrowser)
    manager = SessionManager(settings)

    start_status = asyncio.run(manager.start_handoff())
    complete_status = asyncio.run(manager.complete_handoff())

    assert start_status.status == SessionState.HANDOFF_ACTIVE
    assert complete_status.status == SessionState.READY
    assert FakeBrowser.instances[0].headless is False
    assert FakeBrowser.instances[-1].headless is True
