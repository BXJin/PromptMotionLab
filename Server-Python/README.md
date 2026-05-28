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

## Runtime LLM Smoke Test

Start the server first, then run from the repository root:

```powershell
python scripts\runtime_llm_smoke_test.py --base-url http://localhost:8010
```

The script sends several Korean runtime prompts, checks `reply`, `behavior`, and
`metadata`, then writes CSV/JSON reports under:

```text
Build/reports/
```

## Runtime Streaming API

```text
POST /api/runtime/respond/stream
```

This SSE endpoint sends:

```text
event: reaction
data: immediate thinking/listening Behavior JSON

event: final
data: final reply + behavior + metadata
```

The existing Unreal HTTP client still uses `/api/runtime/respond`. To get the
perceived-latency benefit in Unreal, the client must consume this stream endpoint
and apply the `reaction` event immediately.

## Runtime WebSocket API

```text
WS /ws/runtime
```

Client message:

```json
{
  "type": "runtime_request",
  "requestId": "ue_001",
  "sessionId": "demo_session",
  "characterId": "default_girl",
  "message": "Explain this exhibit.",
  "sceneContext": {}
}
```

Server messages:

```json
{
  "type": "reaction",
  "requestId": "ue_001",
  "behavior": {
    "emotion": "thinking",
    "intensity": 0.45
  }
}
```

```json
{
  "type": "final",
  "requestId": "ue_001",
  "response": {
    "reply": "...",
    "behavior": {},
    "metadata": {}
  }
}
```

Unreal should use this WebSocket path for low-latency runtime interaction and keep
the HTTP endpoint as a fallback/manual test path.

## Runtime Character API

First runtime endpoint for Unreal integration:

```text
POST /api/runtime/respond
```

Runtime response generation uses OpenAI when `OPENAI_API_KEY` or `openai_api_key`
is present. Without a key, or when the provider fails/timeouts, the server falls
back to the deterministic mock provider so Unreal can keep running.

The runtime service keeps a short in-memory conversation history per `sessionId`
and passes recent turns to the active provider. This is intentionally process-local
for the MVP; persistent memory should be added only after the runtime behavior is
stable.

Character profile support is intentionally minimal for the MVP. `default_girl`
and `default_guide` currently provide only persona, speech style, default emotion,
and an emotion intensity scale. Avoid adding long lore or relationship systems
until the single-character conversation loop is stable.

Optional environment variables:

```text
OPENAI_MODEL=gpt-4o-mini
OPENAI_RESPONSES_ENDPOINT=https://api.openai.com/v1/responses
OPENAI_TIMEOUT_SECONDS=6.0
RUNTIME_PROVIDER_TIMEOUT_SECONDS=6.5
RUNTIME_MAX_SESSION_TURNS=40
RUNTIME_TECH_PROFILE=text_llm_behavior_json_v1
RUNTIME_INPUT_MODE=text
RUNTIME_METRICS_CSV_PATH=Server-Python/data/metrics/runtime_latency.csv
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=
AZURE_TTS_VOICE=en-US-JennyNeural
AZURE_TTS_KO_VOICE=ko-KR-SunHiNeural
```

Azure TTS is optional. Without `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`,
the server uses `MockTtsProvider` and returns a silent WAV so the Unreal
audio/lip-sync integration can be developed without cloud credentials.

Install Azure Speech support when needed:

```powershell
pip install -e .[azure]
```

Runtime latency rows are appended to:

```text
Server-Python/data/metrics/runtime_latency.csv
```

Use `RUNTIME_METRICS_CSV_PATH` to move the file, for example to a shared
`Build/metrics` directory.

## Runtime TTS

Generate a Speech Timeline:

```http
POST /api/runtime/tts/synthesize
```

Request:

```json
{
  "text": "Hello. Nice to meet you.",
  "ttsStyle": "warm"
}
```

Download audio:

```http
GET /api/runtime/audio/{utteranceId}.wav
```

The `tech_profile` column records which pipeline or optimization set produced the
measurement, for example `text_llm_behavior_json_v1`, `push_to_talk_stt_v1`, or
`vad_eot_v1`.

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
  },
  "metadata": {
    "provider": "OpenAiRuntimeBehaviorProvider",
    "fallbackUsed": false,
    "providerLatencyMs": 1234
  }
}
```
