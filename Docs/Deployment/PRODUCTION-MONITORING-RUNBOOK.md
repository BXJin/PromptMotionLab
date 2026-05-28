# Production Monitoring Runbook

Updated: 2026-05-27

This runbook defines the minimum monitoring needed before using the PromptMotionLab server for Android or public demo builds.

## Why This Exists

Azure App Service deployment status can be misleading. During one deployment, `az webapp deploy` reported startup failure after waiting too long, while the container logs showed Uvicorn started and the startup probe later succeeded.

The rule is:

```text
Do not judge production health from the deploy command alone.
Use health checks, smoke tests, and runtime logs.
```

## Minimum Checks After Every Deployment

Run:

```powershell
python scripts\production_smoke_test.py
```

Expected checks:

```text
OK   health
OK   docs_disabled
OK   openapi_disabled
OK   runtime_respond
OK   turn_async_submit
OK   turn_async_poll
```

What each check means:

| Check | Purpose |
|---|---|
| `health` | Confirms FastAPI is reachable. |
| `docs_disabled` | Confirms `/docs` is not exposed in production. |
| `openapi_disabled` | Confirms `/openapi.json` is not exposed in production. |
| `runtime_respond` | Confirms LLM + BehaviorJson path works. |
| `turn_async_submit` | Confirms async turn job submission works. |
| `turn_async_poll` | Confirms response + TTS segment readiness. |

## Azure Logs To Check

Live tail:

```powershell
az webapp log tail --resource-group live-3D-character --name Live3DCharacter
```

Download logs:

```powershell
az webapp log download `
  --resource-group live-3D-character `
  --name Live3DCharacter `
  --log-file Build\deploy\Live3DCharacter-logs.zip
```

Important files inside the downloaded logs:

| File | Use |
|---|---|
| `LogFiles/*containerStream.log` | Uvicorn startup, request logs, runtime errors. |
| `LogFiles/StartupLogs/*failure.log` | Import errors, dependency issues, container start failures. |
| `LogFiles/*status.log` | App Service container lifecycle and startup probe state. |
| `LogFiles/kudu/deployment/*.txt` | Oryx build, dependency install, deployment result. |

## Current App-Level Logs

The server also writes local diagnostic files:

| File | Purpose |
|---|---|
| `data/metrics/runtime_latency.csv` | Request latency, provider, route, behavior summary. |
| `data/metrics/runtime_provider_failures.jsonl` | Provider parse/timeout failures. Production samples are redacted. |

Limitations:

- These are local App Service filesystem files.
- They are acceptable for single-instance MVP debugging.
- They are not enough for long-term service monitoring.
- Multi-instance deployment should move these signals to Application Insights or another central log sink.

## Recommended Azure Monitoring

Before public Play Store release, enable:

```text
Application Insights
```

Track at minimum:

| Signal | Alert Threshold |
|---|---|
| `/health` availability | fails 2 times in 5 minutes |
| 5xx response rate | > 2% for 5 minutes |
| `/api/runtime/respond` p95 | > 5 seconds for 10 minutes |
| `/api/runtime/turn/async` submit failures | > 2% for 5 minutes |
| `/api/runtime/turn/jobs/*` failed jobs | > 2% for 5 minutes |
| WebSocket close/error count | sudden spike |
| App Service CPU | > 80% for 10 minutes |
| App Service memory | > 80% for 10 minutes |

## Current Cost Guard

Azure Cost Management budget is configured for the production resource group:

| Field | Value |
|---|---|
| Scope | `live-3D-character` resource group |
| Budget name | `PromptMotionLab-Monthly-Cost-Guard` |
| Amount | `10 USD` monthly |
| Notifications | 50%, 80%, 100% actual cost |
| Email | `bsung472@gmail.com` |
| Start | `2026-05-01T00:00:00Z` |
| End | `2036-05-01T00:00:00Z` |

Important limitation:

```text
Azure Budget notifications are alerts, not a hard spending cap.
```

If the app becomes public, add an Action Group or Automation path that disables or stops the App Service at the 100% threshold. Until then, the budget protects against silent cost growth by notifying the owner.

Cost control alerts:

| Service | Alert |
|---|---|
| OpenAI | daily spend anomaly |
| Azure Speech | daily spend anomaly |
| App Service | budget threshold 50%, 80%, 100% |

## Triage Guide

### Health fails

Check:

1. `containerStream.log`
2. `StartupLogs/*failure.log`
3. App Service Configuration values
4. Startup command

Common causes:

- `ModuleNotFoundError: No module named 'app'`
- bad zip path separators
- missing dependency install
- bad startup command
- app setting typo

### Deploy command says failed, but app may be alive

Run:

```powershell
python scripts\production_smoke_test.py
```

If smoke passes, treat deployment as usable and inspect Kudu logs later.

### Runtime respond fails

Check:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_TIMEOUT_SECONDS`
- provider failure log
- rate limit status

### TTS/segments fail

Check:

- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`
- `AZURE_TTS_KO_VOICE`
- `RUNTIME_TURN_SEGMENT_TTS_ENABLED`
- `TTS_PROVIDER_TIMEOUT_SECONDS`

### Streaming STT fails

Check:

- App Service WebSockets setting is On.
- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`
- `AZURE_STT_LANGUAGE`
- `/ws/stt` client URL uses `wss://`.

## Current Stability Policy

For closed beta/internal testing:

```text
Smoke test passing + logs clean enough = deployable.
```

For public release:

```text
Application Insights + alerts + budget alerts are required.
```
