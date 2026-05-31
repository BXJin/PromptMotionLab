# PromptMotionLab

PromptMotionLab is a realtime 3D AI character conversation demo.

The current product goal is not a text-only chatbot. It is an end-to-end runtime
pipeline where a user speaks to a 3D character, the server generates a short
reply plus behavior JSON, and Unreal applies expression, gaze, gesture, TTS
audio, and lip-sync without blocking local character motion.

```text
Voice input
-> STT
-> LLM reply + Behavior JSON
-> TTS WAV + viseme timeline
-> Unreal face preset blend + lip-sync playback
```

## Repository Layout

| Path | Role |
| --- | --- |
| [`Client-Unreal/PromptMotionClient`](Client-Unreal/PromptMotionClient/README.md) | UE5 client, voice capture, runtime API client, expression/lip-sync playback |
| [`Server-Python`](Server-Python/README.md) | FastAPI server, STT/LLM/TTS providers, async turn orchestration, character profiles |
| `Shared/contracts` | Shared JSON schema/contracts used by the runtime pipeline |
| `scripts` | Smoke tests, deployment packaging, style/eval data helpers |
| `Docs` | Local planning and portfolio notes. Ignored by Git. |

## Runtime Flow

```text
Unreal
  local listening/thinking expression starts immediately
  voice capture sends audio to streaming STT or batch STT fallback

Server-Python
  /ws/stt streams STT final transcript
  /api/runtime/turn-async accepts the user message and returns a job id
  runtime provider routes short social turns to a faster model and complex turns to a stronger model
  TTS segments are generated as soon as reply text segments are available

Unreal
  applies final Behavior JSON
  starts first ready TTS segment
  plays lip-sync visemes against local morph target mappings
```

## Client

Open the Unreal project:

```text
Client-Unreal/PromptMotionClient/PromptMotionClient.uproject
```

Main code map:

| Area | Entry Points |
| --- | --- |
| Runtime orchestration | [`PromptMotionRuntimeComponent`](Client-Unreal/PromptMotionClient/Source/PromptMotionClient/Runtime/Core/PromptMotionRuntimeComponent.h) |
| HTTP/WebSocket API | [`PromptMotionApiClient`](Client-Unreal/PromptMotionClient/Source/PromptMotionClient/Runtime/Core/PromptMotionApiClient.h), [`PromptMotionRealtimeClient`](Client-Unreal/PromptMotionClient/Source/PromptMotionClient/Runtime/Core/PromptMotionRealtimeClient.h) |
| Voice input/STT | [`PromptMotionVoiceInputController`](Client-Unreal/PromptMotionClient/Source/PromptMotionClient/Runtime/Core/PromptMotionVoiceInputController.h), [`PromptMotionStreamingSttClient`](Client-Unreal/PromptMotionClient/Source/PromptMotionClient/Runtime/Core/PromptMotionStreamingSttClient.h) |
| TTS playback | [`PromptMotionSpeechPlaybackController`](Client-Unreal/PromptMotionClient/Source/PromptMotionClient/Runtime/Core/PromptMotionSpeechPlaybackController.h) |
| Face/lip-sync layers | [`FacePresetResolver`](Client-Unreal/PromptMotionClient/Source/PromptMotionClient/Runtime/Face/FacePresetResolver.h), [`FaceLipSyncLayer`](Client-Unreal/PromptMotionClient/Source/PromptMotionClient/Runtime/Face/FaceLipSyncLayer.h) |

See [Client README](Client-Unreal/PromptMotionClient/README.md).

## Server

Run locally:

```powershell
cd Server-Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --port 8010
```

Main code map:

| Area | Entry Points |
| --- | --- |
| API routes | [`app/api/routes.py`](Server-Python/app/api/routes.py) |
| Runtime turn service | [`runtime_character_service.py`](Server-Python/app/services/runtime_character_service.py), [`runtime_turn_async_job_service.py`](Server-Python/app/services/runtime_turn_async_job_service.py) |
| LLM routing/provider | [`routing_openai_provider.py`](Server-Python/app/providers/runtime/routing_openai_provider.py), [`openai_provider.py`](Server-Python/app/providers/runtime/openai_provider.py) |
| Character profile | [`character_profile_store.py`](Server-Python/app/services/character_profile_store.py), [`profile_prompt_builder.py`](Server-Python/app/providers/runtime/profile_prompt_builder.py) |
| STT/TTS | [`stt_service.py`](Server-Python/app/services/stt_service.py), [`tts_service.py`](Server-Python/app/services/tts_service.py) |
| Security/limits | [`app/security`](Server-Python/app/security) |

See [Server README](Server-Python/README.md).

## Current Runtime APIs

```text
GET  /health
POST /api/runtime/respond
POST /api/runtime/turn-async
GET  /api/runtime/turn-async/{job_id}
POST /api/runtime/tts/synthesize
GET  /api/runtime/audio/{utterance_id}.wav
WS   /ws/stt
WS   /ws/runtime
```

## Verification

Server tests:

```powershell
python -m pytest Server-Python\tests
```

Production smoke test:

```powershell
python scripts\production_smoke_test.py
```

Unreal validation is currently done with PIE logs and Android quick launch logs,
checking `RuntimeConfig`, STT final timing, LLM ready timing, TTS ready timing,
first audio start, expression preset blend, and lip-sync playback.
