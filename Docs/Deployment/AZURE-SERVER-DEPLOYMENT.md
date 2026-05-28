# PromptMotionLab Azure Server Deployment

This is the deployment checklist for the FastAPI runtime server used by the Unreal client.

## Target Shape

- Azure App Service, Linux, Python 3.11 or 3.12.
- Server root: `Server-Python`.
- Startup command:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Azure App Service injects the public HTTPS/WSS endpoint. The Unreal client should point to:

```text
https://<app-name>.azurewebsites.net
wss://<app-name>.azurewebsites.net/ws/stt
```

## Required App Service Settings

Copy values from `Server-Python/.env.production.example` into Azure App Service Configuration.

Minimum required secrets:

```text
OPENAI_API_KEY
AZURE_SPEECH_KEY
AZURE_SPEECH_REGION
```

Important production defaults:

```text
OPENAI_MODEL=gpt-4.1-mini
OPENAI_NANO_MODEL=gpt-4.1-nano
OPENAI_ROUTING_ENABLED=1
RUNTIME_TURN_SEGMENT_TTS_ENABLED=1
AZURE_TTS_KO_VOICE=ko-KR-SunHiNeural
AZURE_STT_LANGUAGE=ko-KR
```

## Azure Portal Settings

- Runtime stack: Python 3.11+.
- Platform: 64-bit.
- WebSockets: On.
- Always On: On if the plan supports it.
- HTTPS Only: On.
- Startup Command: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- Health check path: `/health`.

## Deployment Verification

After deployment:

```bash
curl https://<app-name>.azurewebsites.net/health
```

Expected:

```json
{"status":"ok"}
```

Then test the main async turn endpoint:

```bash
curl -X POST https://<app-name>.azurewebsites.net/api/runtime/turn/async \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"안녕\",\"sessionId\":\"deploy_smoke\",\"characterId\":\"default_girl\"}"
```

Expected:

- HTTP 200.
- `turnJobId` exists.
- `reaction` exists.

Then poll:

```bash
curl https://<app-name>.azurewebsites.net/api/runtime/turn/jobs/<turnJobId>
```

Expected:

- `responseReady=true` within a few seconds.
- `speechTimeline` or `segments` appear when TTS is ready.

Automated smoke test:

```powershell
python scripts\production_smoke_test.py
```

See `Docs/Deployment/PRODUCTION-MONITORING-RUNBOOK.md` for deployment triage, Azure log locations, and recommended Application Insights alerts.

## Unreal Production URL

Update:

```ini
[PromptMotion.Runtime]
ActiveProfile=Production

[PromptMotion.Runtime.Production]
ServerUrl=https://live3dcharacter-fqfpbcdhawbjggeq.koreacentral-01.azurewebsites.net
RuntimeWebSocketUrl=wss://live3dcharacter-fqfpbcdhawbjggeq.koreacentral-01.azurewebsites.net/ws/runtime
StreamingSttWebSocketUrl=wss://live3dcharacter-fqfpbcdhawbjggeq.koreacentral-01.azurewebsites.net/ws/stt
```

File:

```text
Client-Unreal/PromptMotionClient/Config/DefaultGame.ini
```

## Notes And Risks

- `requirements.txt` includes `azure-cognitiveservices-speech`; without it, Azure TTS and streaming STT will fail on App Service.
- Runtime WAV files are temporary and cleaned by `TTS_AUDIO_TTL_SECONDS` / `TTS_AUDIO_MAX_FILES`.
- The current audio storage is local App Service filesystem storage, which is acceptable for a single-instance MVP. Multi-instance scale-out should move audio to Blob Storage.
- If the app sleeps on free/basic plans, first response latency will spike. Use Always On for demos.
- App Service must have WebSockets enabled for `/ws/stt`.
- Set `ENVIRONMENT=production` in App Service so FastAPI disables `/docs`, `/redoc`, and `/openapi.json`.
- Keep `RUNTIME_LOG_PRIVATE_DATA=false` in App Service. This redacts provider failure samples so user transcripts and model replies are not stored in production logs by default.
- Keep `RATE_LIMIT_ENABLED=true` for public builds. The current in-memory limiter is suitable for a single B1 instance; multi-instance scale-out should move rate limiting to Redis, Azure API Management, or an edge gateway.
- Keep `WEBSOCKET_STT_MAX_PER_CLIENT` and `WEBSOCKET_RUNTIME_MAX_PER_CLIENT` low during beta because WebSocket sessions can hold Azure Speech and App Service resources open.
