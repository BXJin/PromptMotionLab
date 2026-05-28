# PromptMotionLab Security Risk Assessment

Last updated: 2026-05-27

This document summarizes the main security, privacy, abuse, and deployment risks for shipping PromptMotionLab as an Android app backed by an Azure-hosted FastAPI server.

The current architecture is directionally correct because the mobile APK does not need OpenAI or Azure Speech secrets. The high-risk surface is now the public server API.

## Current Deployment Shape

- Android/Unreal client calls a hosted API over HTTPS/WSS.
- Azure App Service hosts the Python FastAPI server.
- OpenAI and Azure Speech keys are stored as server-side App Service environment variables.
- Runtime conversation uses:
  - `POST /api/runtime/turn/async`
  - polling endpoint for turn job status
  - `GET /api/runtime/audio/{audio_id}.wav`
  - `WS /ws/stt` for streaming STT
- TTS WAV files and viseme timelines are generated server-side.

## Executive Summary

The app is not ready for public Play Store release until public API abuse protection and privacy disclosure are handled.

Critical risks:

1. Public unauthenticated API can be abused to spend OpenAI/Azure quota.
2. Public STT WebSocket can be abused as a long-lived compute connection.
3. Voice/text transcripts are sensitive user data and must be disclosed in Play Store Data Safety and privacy policy.
4. Production APK must never ship localhost, HTTP, debug STT WAV paths, or provider secrets.
5. Server logs currently contain enough user transcript/reply data to become a privacy liability.

## Risk Register

| ID | Risk | Severity | Current Status | Required Before Public Release |
|---|---|---:|---|---|
| SEC-01 | Unauthenticated API cost abuse | Critical | Partially mitigated | Rate limits added; still needs API auth or signed client/session token |
| SEC-02 | Unrestricted resource consumption | Critical | Partially mitigated | Per-IP/session rate limit, request size checks, and WebSocket caps added |
| SEC-03 | API keys leaked in APK | Critical | Mitigated | Keep all provider keys server-side only |
| SEC-04 | Voice privacy disclosure | Critical | Open | Privacy policy, Data Safety form, in-app microphone rationale |
| SEC-05 | Transcript logging | High | Mitigated | Production provider failure logs redact transcript/reply samples by default |
| SEC-06 | TTS audio URL enumeration/replay | High | Partially mitigated | Random IDs, short TTL, optional token binding |
| SEC-07 | Debug endpoints/config in release APK | High | Open | Production profile check before packaging |
| SEC-08 | Plain HTTP traffic | High | Mostly mitigated | Enforce HTTPS/WSS only in production Android build |
| SEC-09 | Prompt/content safety | Medium | Open | Safety policy for self-harm, medical/legal/financial, minors |
| SEC-10 | Azure App Service misconfiguration | Medium | Partially mitigated | Always On, HTTPS Only, WebSockets, budget alerts, monitoring |
| SEC-11 | Denial of service on B1 instance | Medium | Partially mitigated | Concurrency caps, queue limits, rate limits, and WebSocket caps added |
| SEC-12 | Third-party provider outage | Medium | Partially mitigated | Clear fallback UX and provider timeout policy |
| SEC-13 | Audio file path traversal | High | Partially mitigated | Add route-level filename validation and keep absolute path boundary check |
| SEC-14 | Internal error info leakage via WebSocket | Medium | Mitigated | WebSocket client errors now use generic codes |
| SEC-15 | Missing server-side input validation | Medium | Mitigated | Added sampleRate, message length, TTS text, content-type, and ASGI body-size checks |
| SEC-16 | FastAPI debug endpoints exposed in production | Medium | Mitigated in code | Disabled /docs, /redoc, and /openapi.json when `ENVIRONMENT=production` |
| SEC-17 | Default sessionId conversation sharing | Low | Mitigated | Missing sessionId now receives a generated anonymous session id |

## Detailed Risks

### SEC-01: Public Unauthenticated API Cost Abuse

Current state:

- The Azure server is reachable from the public internet.
- Runtime endpoints can trigger OpenAI LLM calls, Azure TTS calls, and Azure Speech STT calls.
- Basic in-memory rate limits now apply to `/api/runtime/*` endpoints.
- Authentication is still not implemented. Anyone who discovers the URL can still call the endpoints until a token/session gate is added.

Impact:

- Unexpected OpenAI/Azure charges.
- App Service CPU/memory exhaustion.
- Poor UX for real users during abuse.
- Possible account quota throttling.

Minimum mitigation:

- Add a lightweight server-issued session token.
- Require the token for `/api/runtime/turn/async`, `/api/runtime/audio/*`, and `/ws/stt`.
- Keep per-IP rate limits enabled.
- Add per-session limits once the client sends a stable session token.
- Return `429 Too Many Requests` with a short retry hint.
- Log rate-limit events without logging full transcripts.

Better production mitigation:

- Put Azure Front Door, API Management, or another gateway in front of the App Service.
- Add WAF/rate-limit rules at the edge.
- Use short-lived signed tokens for audio downloads.

Why this matters:

OWASP API Security Top 10 lists unrestricted resource consumption as a major API risk because API calls consume CPU, memory, bandwidth, storage, and external provider quota.

Reference:

- https://owasp.org/API-Security/editions/2023/en/0x11-t10/

### SEC-02: STT WebSocket Resource Abuse

Current state:

- `/ws/stt` accepts a WebSocket connection and can stream audio into Azure Speech.
- WebSockets are longer lived than normal HTTP requests.
- Basic total and per-client WebSocket connection caps now apply to `/ws/stt` and `/ws/runtime`.

Impact:

- A small number of abusive clients can hold connections open.
- Azure Speech streaming cost can increase quickly.
- App Service worker connection pool can be exhausted.

Minimum mitigation:

- Require session token on WebSocket connection.
- Limit connection duration.
- Limit max bytes per STT session.
- Keep concurrent STT sessions limited per IP/session.
- Close idle or silent connections.
- Treat repeated abnormal closes as suspicious.

Recommended defaults for initial public beta:

- Max STT session duration: 20-30 seconds.
- Max concurrent STT sessions per IP: 1-2.
- Max request rate per IP: low single digits per minute for unauthenticated users.

### SEC-03: Provider Secret Leakage

Current state:

- OpenAI and Azure Speech keys are stored as Azure App Service environment variables.
- This is correct for the current architecture.

Do not:

- Put OpenAI/Azure keys in Unreal config files.
- Put secrets in `DefaultGame.ini`.
- Put secrets in Android assets.
- Build a release APK with `.env` files or local debug JSON.

Recommended production hardening:

- Move secrets from raw App Service settings to Azure Key Vault.
- Use Managed Identity from App Service to read Key Vault.
- Rotate keys before public launch if they were ever pasted into logs, screenshots, or shared chat.

Reference:

- https://learn.microsoft.com/en-us/azure/app-service/overview-security

### SEC-04: Voice and Transcript Privacy

Current state:

- The app records microphone audio.
- Audio is sent to the server for STT.
- Transcripts are sent to an LLM provider.
- TTS response audio is generated server-side.

This is personal and sensitive user data for Play Store purposes. Google explicitly includes microphone data in personal and sensitive user data.

Required before Play Store:

- Privacy policy URL.
- Play Console Data Safety form.
- In-app microphone permission rationale.
- Clear disclosure that speech is sent to a server and third-party AI providers for transcription and response generation.
- Contact or deletion request path.

Minimum privacy policy content:

- What is collected: microphone audio, transcript text, conversation responses, technical logs.
- Why it is collected: real-time voice conversation with a 3D character.
- Where it is processed: Azure-hosted server and AI providers.
- Retention: ideally no raw audio retention; short-lived TTS WAV cache; limited logs.
- Sharing: OpenAI/Azure processing as service providers.
- User control: microphone permission can be revoked; contact for deletion.

Reference:

- https://support.google.com/googleplay/android-developer/answer/10144311
- https://developer.android.com/privacy

### SEC-05: Production Transcript Logging

Current state:

- Development logs include STT transcripts, LLM replies, provider names, timings, and audio metadata.
- This is useful for engineering but too sensitive for public production.
- Production provider failure logs now redact model output samples and user-message samples by default when `ENVIRONMENT=production`.
- `RUNTIME_LOG_PRIVATE_DATA=true` can temporarily re-enable raw samples for local debugging only.

Impact:

- Logs can contain private speech.
- Logs can accidentally capture emotional, medical, workplace, or personal content.
- App Service log access becomes a privacy boundary.

Minimum mitigation:

- Keep production log mode enabled.
- Keep latency numbers.
- Remove or hash transcript/reply text.
- Keep request id, provider, status, latency, fallback flag, and segment count.

Suggested production log shape:

```text
VoiceLatency request=42 mode=ptt stt_ms=1225 llm_ms=2072 tts_ready_ms=614 audio_start_ms=4022 provider=openai fallback=false transcript_chars=18 reply_chars=41
```

Avoid:

```text
Transcribed: "..."
reply: ...
```

### SEC-06: TTS Audio URL Access

Current state:

- Generated WAV files are fetched through `/api/runtime/audio/{audio_id}.wav`.
- IDs appear random, which reduces casual guessing.

Risk:

- Anyone with the URL can replay the audio while it exists.
- If IDs are logged or leaked, another client can fetch them.
- If cache TTL is long, old conversation audio can remain available.

Minimum mitigation:

- Keep random, high-entropy audio IDs.
- Short TTL for generated audio.
- Delete expired audio aggressively.
- Do not log full audio URLs in production.

Better mitigation:

- Bind audio downloads to a session token.
- Use signed one-time or short-lived URLs.

### SEC-07: Debug Configuration in Release APK

Current state:

- Unreal runtime supports profiles such as `Local` and `Production`.
- This is good, but packaging must verify the active profile.

Release APK must not include:

- `http://localhost:8010`
- `ws://127.0.0.1:8010/ws/stt`
- debug WAV paths
- debug transcript injection
- verbose viseme debug logs
- local provider keys

Release APK should use:

- `https://live3dcharacter-fqfpbcdhawbjggeq.koreacentral-01.azurewebsites.net`
- `wss://live3dcharacter-fqfpbcdhawbjggeq.koreacentral-01.azurewebsites.net/ws/stt`

Recommended release gate:

- Add a packaging checklist item that fails if `ActiveProfile=Local`.
- Search packaged config for localhost before upload.

### SEC-08: Cleartext HTTP

Current state:

- Azure endpoint supports HTTPS/WSS.
- Local development uses HTTP/WS.

Risk:

- If HTTP ships in production, network observers can inspect or alter requests.
- Speech transcripts and generated replies would be exposed.

Required:

- Use HTTPS/WSS for production.
- Keep Android cleartext disabled for production domains.
- Do not add a broad cleartext network security exception.

Reference:

- https://developer.android.com/privacy-and-security/risks/cleartext-communications

### SEC-09: Prompt and Content Safety

Current state:

- The character can answer general conversation.
- Real users may discuss sadness, self-harm, medical concerns, legal issues, finances, sexual topics, or minors.

Risk:

- Harmful advice.
- Misleading latest-information answers.
- Inappropriate relationship or emotional dependency patterns.
- Store review risk if the character gives unsafe guidance.

Minimum mitigation:

- Add a safety prompt/policy layer.
- Self-harm: supportive response plus emergency recommendation.
- Medical/legal/financial: non-professional disclaimer and encourage qualified help.
- Latest facts: say it cannot verify real-time information unless a browsing/RAG source exists.
- Minors/sexual content: strict refusal and safe redirection.

Product note:

This is not only a compliance issue. It directly affects user trust because the app presents the response through a human-like 3D character.

### SEC-10: Azure App Service Configuration

Current state:

- Azure App Service is running on B1.
- HTTPS endpoint is working.
- WebSockets are working.
- Always On is enabled after B1 upgrade.

Required production checks:

- HTTPS Only: enabled.
- WebSockets: enabled.
- Always On: enabled.
- 64-bit worker: enabled.
- App Service logs: retention configured.
- Budget alerts: configured.
- Health check: configured if using a scale plan or deployment slots.

Recommended:

- Add Azure budget alert at a low threshold during beta.
- Set OpenAI and Azure Speech quota limits where available.
- Monitor App Service CPU/memory and HTTP 5xx.

Reference:

- https://learn.microsoft.com/en-us/azure/app-service/overview-security

### SEC-11: B1 Capacity and Denial of Service

Current state:

- B1 is enough for early beta and demos, but not a public abuse-resistant tier.
- LLM/TTS/STT calls are external and can pile up under load.

Risk:

- 502/503 errors.
- Long LLM fallback timeouts.
- WebSocket instability.
- High cloud bill.

Minimum mitigation:

- Keep server-side concurrency caps.
- Queue or reject requests beyond capacity.
- Return clear fallback messages instead of hanging.
- Add rate limits before public distribution.

Suggested launch stance:

- Internal testing: B1 acceptable.
- Closed beta: B1 acceptable with rate limits and budget alerts.
- Public Play Store: consider a gateway/rate-limit layer before scaling compute.

### SEC-12: Third-Party Provider Outage and Fallback UX

Current state:

- Server has provider timeout and fallback behavior.
- Recent testing showed fallback can occur when provider latency spikes.

Risk:

- User sees a generic "try again" message.
- The character may appear broken if fallback is too frequent.

Required:

- Keep timeout and fallback deterministic.
- Log fallback counts without storing transcripts.
- Track fallback rate as a release quality metric.

Suggested threshold:

- Internal demo: fallback under 10% may be acceptable.
- Closed beta: target under 3%.
- Public release: target under 1-2% for normal short Korean prompts.

### SEC-13: Audio File Path Traversal

Current state:

- `GET /api/runtime/audio/{filename}` passes `filename` directly to `service.resolve_audio_path(filename)`.
- There is no validation in the route layer that `filename` is a plain filename without path components.
- `resolve_audio_path` already resolves the candidate path and checks that it stays under the configured audio root. This is a useful first mitigation, but the route should still reject suspicious filenames before path resolution.

Risk:

- If future changes weaken `resolve_audio_path`, a request such as `GET /api/runtime/audio/../../etc/passwd` or `GET /api/runtime/audio/../app/dependencies.py` could resolve outside the intended audio directory.
- On Linux/container deployments, this class of bug can expose server source files, environment files, or other application state.

Minimum mitigation:

- Reject any `filename` that contains `/`, `\`, or `..` before passing to `resolve_audio_path`.
- In `resolve_audio_path`, resolve the absolute path and assert it remains inside the expected audio directory using `relative_to` or parent containment. Avoid simple string prefix checks.

Recommended code pattern:

```python
AUDIO_DIR = Path(...)  # known safe base

def resolve_audio_path(filename: str) -> Path | None:
    if "/" in filename or "\\" in filename or ".." in filename:
        return None
    if not filename.endswith(".wav"):
        return None
    resolved = (AUDIO_DIR / filename).resolve()
    root = AUDIO_DIR.resolve()
    if root not in resolved.parents:
        return None
    return resolved if resolved.exists() else None
```

### SEC-14: Internal Error Information Leakage via WebSocket

Current state:

- The `/ws/runtime` and `/ws/stt` WebSocket handlers now return generic error codes to clients:

```python
# ws/runtime
"error": "runtime_failed"

# ws/stt
"error": "streaming_stt_failed"
```

- Before this mitigation, the handlers included exception class names in client-visible error payloads.

Risk:

- Exception class names reveal internal implementation details such as module structure, third-party SDK names, and failure modes.
- An attacker can use this information to target specific code paths.
- Examples: `AzureSpeechSDKException`, `OpenAIAuthenticationError`, `ConnectionRefusedError` all provide useful signals.

Minimum mitigation:

- Keep class names out of client-visible error payloads.
- Log the real exception server-side with a request/correlation ID.
- Return only the correlation ID to the client for support purposes.

Suggested production error shape:

```json
{ "type": "error", "error": "runtime_failed", "requestId": "..." }
```

### SEC-15: Missing Server-Side Input Validation

Current state:

Several fields from WebSocket or HTTP request payloads now have basic server-side validation. This should remain covered by regression tests because these checks protect cloud cost and provider stability.

**sampleRate (ws/stt)**:

The server accepts only known STT sample rates such as `8000`, `16000`, `24000`, and `48000`.

**message length (all runtime endpoints)**:

Runtime message text is capped before it is sent to the OpenAI LLM provider. This limits accidental token spikes and intentionally oversized prompts.

**audio content-type (STT upload)**:

`POST /api/runtime/stt/transcribe` validates known audio content types and applies an ASGI body-size limit before the route reads the full body. This protects both normal `Content-Length` requests and clients that omit the header.

Minimum mitigation:

- Keep the allowed `sampleRate` list narrow.
- Keep `message` and TTS text caps aligned with the product UX.
- Keep the ASGI body-size middleware active for STT upload routes.

### SEC-16: FastAPI Debug Endpoints Exposed in Production

Current state:

- FastAPI exposes `/docs` (Swagger UI) and `/redoc` (ReDoc) by default.
- `main.py` now disables `/docs`, `/redoc`, and `/openapi.json` when `ENVIRONMENT=production`.

Risk:

- The full API schema, all endpoint paths, request and response shapes, and example payloads are publicly browsable.
- An attacker learns the exact request format for all endpoints including `/ws/stt` and `/api/runtime/turn/async` without any reverse engineering.
- This is a significant reconnaissance advantage.

Minimum mitigation:

- Keep docs disabled in production startup:

```python
app = FastAPI(
    ...
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/docs",
    redoc_url=None if os.getenv("ENVIRONMENT") == "production" else "/redoc",
    openapi_url=None if os.getenv("ENVIRONMENT") == "production" else "/openapi.json",
)
```

- Set `ENVIRONMENT=production` as an Azure App Service environment variable.

### SEC-17: Default sessionId Conversation Sharing

Current state:

- Runtime requests now generate a unique anonymous session id if no `sessionId` is provided:

```python
session_id = f"anon_{uuid4().hex}"
```

- Conversation memory is keyed by session ID.
- Older demos and docs used `"demo_session"` as the default, which is not safe for public multi-user deployments.

Risk:

- Multiple real users who do not send a sessionId will share the same conversation history.
- At an exhibition or public deployment, one user's conversation leaks into another user's session.
- This is a privacy issue as well as a functional correctness issue.

Minimum mitigation:

- Do not reintroduce a hardcoded fallback session ID in production.
- Prefer a stable per-device session id from the client when conversation continuity matters.
- Use server-generated anonymous session IDs only as a privacy-safe fallback.

## Release Readiness Checklist

### Must Fix Before Public Play Store

- [ ] Add API authentication or signed session token.
- [x] Add initial per-IP runtime rate limits.
- [x] Add WebSocket session caps.
- [ ] Add signed per-session token and session-bound limits.
- [x] Disable transcript/reply samples in production provider failure logs.
- [ ] Confirm production APK uses HTTPS/WSS only.
- [ ] Confirm no localhost/debug URLs in packaged config.
- [ ] Create privacy policy URL.
- [ ] Complete Google Play Data Safety form.
- [ ] Add microphone permission rationale.
- [ ] Configure Azure budget alerts.
- [ ] Confirm generated TTS audio TTL cleanup.

### Should Fix Before Closed Beta

- [ ] Add server-side request size limits.
- [ ] Add structured production latency logs.
- [ ] Add fallback rate dashboard or report script.
- [ ] Add Play Store test account/reviewer instructions.
- [ ] Add content safety policy for self-harm and professional advice.
- [ ] Add endpoint health check documentation.
- [x] Validate `filename` path traversal in `resolve_audio_path` (SEC-13).
- [x] Replace exception class names in WebSocket error messages with opaque codes (SEC-14).
- [x] Add `sampleRate` range validation, `message` length cap, and ASGI body-size limit (SEC-15).
- [x] Disable FastAPI `/docs`, `/redoc`, `/openapi.json` when `ENVIRONMENT=production` (SEC-16).
- [x] Require or generate a unique `sessionId` per device; remove `"demo_session"` fallback (SEC-17).

### Can Wait Until After MVP

- [ ] Move secrets to Key Vault with Managed Identity.
- [ ] Put API Management or Azure Front Door in front of App Service.
- [ ] Add Redis-backed distributed rate limiting for multi-instance scale-out.
- [ ] Add per-user accounts.
- [ ] Add user-facing conversation deletion portal.

## Recommended Implementation Order

1. Production log redaction.
2. In-memory FastAPI rate limiting for current B1 single-instance deployment.
3. Short-lived session token for runtime endpoints.
4. TTS audio TTL verification and cleanup.
5. Android release profile audit.
6. Privacy policy and Play Store Data Safety draft.
7. APK packaging and real-device HTTPS/WSS test.

This order reduces the biggest public-release risks before spending time on packaging polish.

## Security Acceptance Criteria for First Public Build

The first public build should not be uploaded until all of the following are true:

- A user cannot call expensive endpoints repeatedly without hitting a quota.
- A user cannot open unlimited STT WebSocket streams.
- No provider key exists in the APK.
- No transcript or reply content is stored in production logs by default.
- The app clearly discloses microphone/network AI processing.
- The production APK only points at HTTPS/WSS endpoints.
- Azure cost alerts are active.
- The server can return controlled fallback responses under provider failure.

## References

- OWASP API Security Top 10 2023: https://owasp.org/API-Security/editions/2023/en/0x11-t10/
- Azure App Service security overview: https://learn.microsoft.com/en-us/azure/app-service/overview-security
- Google Play User Data policy: https://support.google.com/googleplay/android-developer/answer/10144311
- Android privacy guidance: https://developer.android.com/privacy
- Android cleartext communications risk: https://developer.android.com/privacy-and-security/risks/cleartext-communications
