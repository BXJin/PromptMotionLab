# PromptMotionLab Server

FastAPI backend for the realtime 3D AI character runtime.

The server owns speech recognition, LLM behavior planning, TTS generation,
character profile prompting, short-session history, safety/limit checks, and
latency logging. Unreal owns the visible character execution.

```text
transcript/message
-> RuntimeCharacterService
-> Runtime provider routing
-> reply + BehaviorJson
-> async TTS segments + viseme timeline
-> Unreal playback
```

## Run Locally

```powershell
cd Server-Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --port 8010
```

Health check:

```powershell
Invoke-WebRequest http://localhost:8010/health -UseBasicParsing
```

## Environment

Minimum local LLM/STT/TTS setup:

```text
OPENAI_API_KEY=
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=koreacentral
```

Common runtime settings:

```text
OPENAI_MODEL=gpt-4.1-mini
OPENAI_FAST_MODEL=gpt-4.1-nano
OPENAI_TIMEOUT_SECONDS=6.0
RUNTIME_PROVIDER_TIMEOUT_SECONDS=6.5
RUNTIME_MAX_SESSION_TURNS=40
RUNTIME_OPENAI_HISTORY_TURNS=20
RUNTIME_METRICS_CSV_PATH=Server-Python/data/metrics/runtime_latency.csv
AZURE_TTS_KO_VOICE=ko-KR-SunHiNeural
```

Without Azure Speech settings, the app can still use mock/fallback providers for
contract testing, but the full voice demo needs Azure Speech.

## Runtime APIs

| API | Role |
| --- | --- |
| `GET /health` | App Service and local health check |
| `POST /api/runtime/respond` | Synchronous text runtime response |
| `POST /api/runtime/turn-async` | Starts async reply/TTS job and returns immediate reaction |
| `GET /api/runtime/turn-async/{job_id}` | Polls async final reply and TTS segment readiness |
| `POST /api/runtime/tts/synthesize` | Creates WAV + viseme timeline for text |
| `GET /api/runtime/audio/{utterance_id}.wav` | Downloads generated audio |
| `WS /ws/stt` | Streaming STT endpoint used by Unreal PTT |
| `WS /ws/runtime` | Runtime WebSocket path for low-latency experiments |

## Key Code

### API

| File | Role |
| --- | --- |
| [`app/main.py`](app/main.py) | FastAPI app construction and middleware setup |
| [`app/api/routes.py`](app/api/routes.py) | HTTP and WebSocket route definitions |
| [`app/dependencies.py`](app/dependencies.py) | Provider/service wiring from environment variables |

### Runtime Conversation

| File | Role |
| --- | --- |
| [`app/services/runtime_character_service.py`](app/services/runtime_character_service.py) | Main reply pipeline, session history, provider fallback, behavior guard |
| [`app/services/runtime_turn_async_job_service.py`](app/services/runtime_turn_async_job_service.py) | Async turn jobs that let Unreal start reaction before TTS completion |
| [`app/services/runtime_session_store.py`](app/services/runtime_session_store.py) | In-memory short-term session history |
| [`app/services/runtime_scenario_service.py`](app/services/runtime_scenario_service.py) | Small scenario layer, such as repeated emotional disclosure and focused object explanation |

### LLM Providers

| File | Role |
| --- | --- |
| [`app/providers/runtime/routing_openai_provider.py`](app/providers/runtime/routing_openai_provider.py) | Routes short social turns to fast model and complex turns to stronger model |
| [`app/providers/runtime/openai_provider.py`](app/providers/runtime/openai_provider.py) | OpenAI Responses API call, JSON parsing, behavior normalization |
| [`app/providers/runtime/fast_path_provider.py`](app/providers/runtime/fast_path_provider.py) | Deterministic cheap replies for common greetings/fallbacks |
| [`app/providers/runtime/mock_provider.py`](app/providers/runtime/mock_provider.py) | Deterministic provider for tests and fallback |

### Character Profile

| File | Role |
| --- | --- |
| [`app/services/character_profile_store.py`](app/services/character_profile_store.py) | Airi profiles and MBTI-style aliases |
| [`app/providers/runtime/profile_prompt_builder.py`](app/providers/runtime/profile_prompt_builder.py) | Converts profile values and few-shot examples into model instructions |
| [`app/contracts/character_profile.py`](app/contracts/character_profile.py) | Profile contract |

### Speech

| File | Role |
| --- | --- |
| [`app/services/stt_service.py`](app/services/stt_service.py) | Batch STT service wrapper |
| [`app/providers/stt/streaming_factory.py`](app/providers/stt/streaming_factory.py) | Selects the `/ws/stt` streaming provider from `STREAMING_STT_PROVIDER` |
| [`app/providers/stt/azure_streaming_provider.py`](app/providers/stt/azure_streaming_provider.py) | Azure streaming STT provider, default production path |
| [`app/providers/stt/openai_realtime_streaming_provider.py`](app/providers/stt/openai_realtime_streaming_provider.py) | OpenAI Realtime transcription provider for low-latency STT comparison |
| [`app/providers/stt/google_streaming_provider.py`](app/providers/stt/google_streaming_provider.py) | Google Speech-to-Text streaming provider, optional dependency |
| [`app/providers/stt/openai_provider.py`](app/providers/stt/openai_provider.py) | OpenAI batch STT fallback/debug path |
| [`app/services/tts_service.py`](app/services/tts_service.py) | TTS orchestration and timeline response |
| [`app/services/tts_async_job_service.py`](app/services/tts_async_job_service.py) | Async TTS segment generation for turn jobs |
| [`app/providers/tts/azure_provider.py`](app/providers/tts/azure_provider.py) | Azure TTS WAV and viseme generation |
| [`app/providers/tts/wav_trim.py`](app/providers/tts/wav_trim.py) | WAV post-processing helpers |

Streaming STT selection:

```env
STREAMING_STT_PROVIDER=azure   # azure | openai | google
STREAMING_STT_LANGUAGE=ko-KR
```

Google streaming STT is optional to keep Azure App Service deployment light. Install `requirements-stt-google.txt` before selecting `STREAMING_STT_PROVIDER=google`.

### Security And Ops

| File | Role |
| --- | --- |
| [`app/security/rate_limit.py`](app/security/rate_limit.py) | In-memory request rate limiting |
| [`app/security/body_size_limit.py`](app/security/body_size_limit.py) | Request body size guard |
| [`app/security/websocket_limits.py`](app/security/websocket_limits.py) | WebSocket message/audio limits |
| [`app/security/log_redaction.py`](app/security/log_redaction.py) | Production transcript/reply redaction helpers |
| [`app/services/latency_metrics_logger.py`](app/services/latency_metrics_logger.py) | CSV latency metrics writer |

## Behavior JSON Contract

The LLM does not output morph targets directly. It returns compact behavior:

```json
{
  "reply": "오, 뭐 봤어?",
  "behavior": {
    "emotion": "friendly",
    "intensity": 0.55,
    "confidence": 0.82,
    "intent": "answer",
    "gaze": "user",
    "gestureKey": "small_ack",
    "headMotion": "small_nod",
    "ttsStyle": "warm"
  }
}
```

Unreal maps this to stable local presets. This keeps latency and animation
quality under client control.

## Tests

Run all server tests from the repository root:

```powershell
python -m pytest Server-Python\tests
```

Focused runtime checks:

```powershell
python -m pytest Server-Python\tests\test_api.py -k "runtime_service or openai_provider"
```

TTS first-segment latency comparison:

```powershell
cd Server-Python
python scripts\benchmark_runtime_turn_tts_latency.py
```

This benchmark compares full-turn TTS against segmented TTS. The important
number is `first_timeline_ms`: Unreal can start downloading and playing the
first ready segment once this appears, while later segments continue to build.

Production smoke test from the repository root:

```powershell
python scripts\production_smoke_test.py
```

## Deployment

Current Azure App Service deployment uses a zip package with `startup.sh`.
The startup script creates a persistent virtual environment under `/home/site`
and runs:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

This avoids repeated Oryx package-build delays and keeps restart time predictable
after the first dependency install.
