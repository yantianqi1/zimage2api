from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Settings
from main import create_app


class FakeSessionManager:
    def __init__(self, status="ready", handoff_url=None):
        self.status = status
        self.handoff_url = handoff_url
        self.started = False
        self.completed = False
        self.refreshed = False
        self.ready = status == "ready"

    async def startup(self):
        return None

    async def shutdown(self):
        return None

    async def get_status(self):
        return {
            "status": self.status,
            "ready": self.ready,
            "handoff_url": self.handoff_url,
            "message": None,
        }

    async def start_handoff(self):
        self.started = True
        self.status = "handoff_active"
        self.handoff_url = "http://novnc.local/?token=abc"
        self.ready = False
        return await self.get_status()

    async def complete_handoff(self):
        self.completed = True
        self.status = "ready"
        self.ready = True
        return await self.get_status()

    async def refresh(self):
        self.refreshed = True
        return await self.get_status()

    async def require_ready(self):
        if not self.ready:
            raise RuntimeError("session_required")


class FakeTaskQueue:
    def __init__(self):
        self.created = []

    async def create_task(self, **kwargs):
        self.created.append(kwargs)
        return kwargs

    async def execute_task(self, task_id):
        return None

    async def get_task(self, task_id):
        return None

    async def get_queue_info(self):
        return {
            "pending_count": len(self.created),
            "processing_count": 0,
            "completed_count": 0,
            "failed_count": 0,
            "total_count": len(self.created),
        }


def build_client(session_status="ready"):
    settings = Settings(API_KEY="test-secret", HANDOFF_ENABLED=True)
    session_manager = FakeSessionManager(status=session_status)
    task_queue = FakeTaskQueue()
    app = create_app(
        settings=settings,
        session_manager=session_manager,
        task_queue=task_queue,
    )
    return TestClient(app), session_manager, task_queue


def auth_headers():
    return {"Authorization": "Bearer test-secret"}


def test_create_app_without_running_event_loop():
    app = create_app(
        settings=Settings(API_KEY="test-secret"),
        session_manager=FakeSessionManager(),
        task_queue=FakeTaskQueue(),
    )

    assert app is not None


def test_session_routes_share_configured_api_key():
    client, _, _ = build_client()

    unauthorized = client.get("/api/v1/session/status")
    assert unauthorized.status_code == 401

    authorized = client.get("/api/v1/session/status", headers=auth_headers())
    assert authorized.status_code == 200
    assert authorized.json()["status"] == "ready"


def test_handoff_start_returns_remote_url():
    client, session_manager, _ = build_client(session_status="needs_human")

    response = client.post("/api/v1/session/handoff/start", headers=auth_headers())

    assert response.status_code == 200
    assert session_manager.started is True
    assert response.json()["status"] == "handoff_active"
    assert response.json()["handoff_url"] == "http://novnc.local/?token=abc"


def test_generate_rejects_requests_when_session_not_ready():
    client, _, task_queue = build_client(session_status="needs_human")

    response = client.post(
        "/api/v1/generate",
        headers=auth_headers(),
        json={"prompt": "test prompt", "size": "1024x1024"},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "session_required"
    assert task_queue.created == []
