import asyncio

import pytest
from fastapi.testclient import TestClient

from app.contracts.runtime_behavior import BehaviorJson, SceneContext
from app.dependencies import get_runtime_character_service
from app.main import app
from app.providers.runtime import RuntimeBehaviorProvider
from app.services import RuntimeCharacterService


@pytest.fixture(autouse=True)
def disable_real_openai_for_tests(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("openai_api_key", raising=False)
    get_runtime_character_service.cache_clear()
    yield
    get_runtime_character_service.cache_clear()


def test_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_generate_procedural_wave() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/generate/procedural",
        json={
            "prompt": "웃으면서 오른손으로 손 흔들어줘",
            "skeletonPreset": "ue5_manny",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["motionSpec"]["gesture"] == "wave"
    assert payload["proceduralGesture"]["gesture"] == "wave"
    assert payload["proceduralGesture"]["skeletonPreset"] == "ue5_manny"


def test_generate_enriched_prompt_export() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/generate/enriched-prompt",
        json={
            "prompt": "웃으면서 오른손으로 손 흔들어줘",
            "skeletonPreset": "ue5_manny",
        },
    )

    assert response.status_code == 200
    export = response.json()["export"]
    assert export["exportId"].startswith("prompt_")
    assert export["originalPrompt"] == "웃으면서 오른손으로 손 흔들어줘"
    assert "right hand" in export["enrichedPrompt"]


def test_runtime_respond_object_explanation() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/runtime/respond",
        json={
            "sessionId": "demo_session",
            "characterId": "default_guide",
            "message": "Explain this exhibit.",
            "sceneContext": {
                "locationId": "demo_hall",
                "focusedObjectId": "exhibit_01",
                "nearbyObjectIds": ["exhibit_01", "exhibit_02"],
                "interactionMode": "object_selected",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reply"]
    assert payload["behavior"]["intent"] == "explain"
    assert payload["behavior"]["gaze"] == "focused_object"
    assert payload["behavior"]["gestureKey"] == "explain_small"


def test_runtime_respond_uncertain_message() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/runtime/respond",
        json={
            "message": "I am not sure about this.",
            "sceneContext": {"focusedObjectId": "exhibit_02"},
        },
    )

    assert response.status_code == 200
    behavior = response.json()["behavior"]
    assert behavior["emotion"] == "uncertain"
    assert behavior["confidence"] < 0.5
    assert behavior["gestureKey"] == "hesitate"


def test_runtime_service_falls_back_when_primary_provider_fails() -> None:
    class FailingProvider(RuntimeBehaviorProvider):
        async def respond(
            self,
            message: str,
            scene_context: SceneContext,
            character_id: str,
        ) -> tuple[str, BehaviorJson]:
            raise RuntimeError("forced failure")

    service = RuntimeCharacterService(primary_provider=FailingProvider(), provider_timeout_seconds=0.1)

    reply, behavior = asyncio.run(service.respond("hello", SceneContext(), "default_guide"))

    assert reply
    assert behavior.intent == "greet"
