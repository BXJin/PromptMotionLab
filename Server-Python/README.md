# PromptMotionLab Server

FastAPI backend for the first MVP pipeline:

```text
prompt -> MotionSpec -> ProceduralGestureJson
prompt + MotionSpec -> EnrichedPromptExport
message + SceneContext -> reply + BehaviorJson
```

This server intentionally does not depend on PyTorch. Local Gemma/Qwen/Llama support belongs in a later isolated worker.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --port 8010
```

## Verify

```powershell
python -m compileall app
python -m app.self_check
```

## Runtime Character API

First runtime endpoint for Unreal integration:

```text
POST /api/runtime/respond
```

Runtime response generation uses OpenAI when `OPENAI_API_KEY` or `openai_api_key`
is present. Without a key, or when the provider fails/timeouts, the server falls
back to the deterministic mock provider so Unreal can keep running.

Optional environment variables:

```text
OPENAI_MODEL=gpt-4o-mini
OPENAI_RESPONSES_ENDPOINT=https://api.openai.com/v1/responses
OPENAI_TIMEOUT_SECONDS=4.0
RUNTIME_PROVIDER_TIMEOUT_SECONDS=4.5
```

Example body:

```json
{
  "sessionId": "demo_session",
  "characterId": "default_guide",
  "message": "Explain this exhibit.",
  "sceneContext": {
    "locationId": "demo_hall",
    "focusedObjectId": "exhibit_01",
    "nearbyObjectIds": ["exhibit_01", "exhibit_02"],
    "interactionMode": "object_selected"
  }
}
```

Example response:

```json
{
  "reply": "exhibit_01 is the current focus. I will look toward it and explain the key point in a concise way.",
  "behavior": {
    "emotion": "friendly",
    "intensity": 0.62,
    "confidence": 0.86,
    "intent": "explain",
    "gaze": "focused_object",
    "gestureKey": "explain_small",
    "headMotion": "small_nod",
    "ttsStyle": "warm"
  }
}
```
