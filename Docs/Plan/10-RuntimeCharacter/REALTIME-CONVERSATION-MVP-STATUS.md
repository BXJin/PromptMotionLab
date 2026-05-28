# Realtime Conversation MVP Status

Last updated: 2026-05-21

## Purpose

This document tracks the current state of the realtime conversation pipeline for PromptMotionLab.

Current scope is face-only.

Gesture, head motion, gaze IK, and full-body animation are intentionally deferred. The target is low-latency conversational feel driven by facial expression, TTS, and lip-sync.

The MVP target:

1. User speaks or types.
2. Character reacts immediately with a thinking/listening face preset.
3. Server returns final reply and behavior.
4. TTS audio and viseme timeline arrive.
5. Unreal plays audio and drives lip-sync plus expression blending.

Everything else, including gesture, head motion, gaze IK, and body animation, is out of scope until this loop feels genuinely responsive.

## 2026-05-21 Working Checklist

This section reflects the current implementation state after the runtime character matrix/stress test work.

### What The Current Python Matrix Tests Validate

The Python matrix tests are for server-side conversation stability, not final Unreal rendering quality.

They validate:

- Prompt behavior stability.
- `mini` / `nano` model routing.
- Character profile tone differences.
- Behavior JSON enum stability.
- Emotion / intent guard behavior.
- Fallback and provider failure rate.
- Response/TTS readiness latency baseline.
- CSV / JSON / summary report generation.

They do not validate:

- Actual Unreal audio playback start timing.
- First viseme application timing.
- Lip-sync visual quality.
- Mouth conflict between expression and speech.
- Gaze/head/body animation quality.
- Real STT/VAD/EoT behavior.

Current report outputs:

```text
Build/reports/runtime_character_matrix/*.csv
Build/reports/runtime_character_matrix/*.json
Build/reports/runtime_character_matrix/*_summary.json
```

Run the normal daily-conversation matrix:

```bat
python scripts\runtime_character_matrix_test.py
```

Run the stress matrix:

```bat
python scripts\runtime_character_matrix_test.py --cases Docs\Plan\10-RuntimeCharacter\runtime_character_stress_cases.json
```

Provider parse/validation/timeout failures are logged here:

```text
Server-Python/data/metrics/runtime_provider_failures.jsonl
```

### Implemented Since The Previous Status

- OpenAI `gpt-4.1-nano` / `gpt-4.1-mini` routing.
- 8 runtime character personality profiles.
- Character profile prompt builder.
- Runtime matrix test runner with CSV/JSON/summary output.
- Stress case file for ambiguous emotional/apology/follow-up prompts.
- Route/model/fallback validation in matrix results.
- p95/max latency summary by model, route, and character.
- Behavior enum normalization, including common emotion aliases.
- Provider failure JSONL logging for parse/validation and timeout failures.
- Apology/emotional guard improvements.
- Fallback route labeling.
- Latency CSV route-column migration for old metric files.
- Sentence-level TTS segments in `turn/async`.
  - LLM still completes first.
  - Server splits final reply into sentence segments.
  - First segment timeline is exposed as soon as it is synthesized.
  - `speechTimeline.segments[]` contains segment-local audio and visemes.

### Current Decision

The current Python test phase is the prompt/answer/behavior stabilization phase.

Proceed to Unreal/audio/lip-sync implementation only after:

- Normal matrix remains roughly stable at `140+ / 144` pass.
- Stress matrix failures are understood and either fixed or intentionally accepted.
- New `runtime_provider_failures.jsonl` entries are reviewed after each run.
- Fallbacks are mostly timeout/network-related, not JSON schema instability.

### Next Implementation Checklist

1. Finish server conversation stability checks.
   - Run normal matrix.
   - Run stress matrix.
   - Review summary, CSV issues, and provider failure log together.
   - Fix only real prompt/guard/routing failures, not acceptable personality variation.

2. Connect Unreal to sentence-level TTS queue.
   - Server-side segment timeline contract exists in `turn/async`.
   - Unreal still needs segment queue playback.
   - Existing direct `/api/runtime/tts/synthesize` remains whole-text TTS.

3. Add Unreal speech segment queue.
   - Read `speechTimeline.segments[]`.
   - Queue audio segments.
   - Play next segment when current segment ends.
   - Use segment-local viseme timelines.
   - Log `audio_play_start_ms` and `first_viseme_applied_ms` via `UE_LOG` first.
   - Do not add a server metrics POST endpoint yet.

4. Continue sentence-level TTS server tuning.
   - Keep REST/async structure for now.
   - Wait for full LLM response.
   - Synthesize segment 1 first and expose it through `speechTimeline`.
   - Queue later segments in `speechTimeline.segments[]`.
   - Do not require SSE/WebSocket for this phase.

5. Add lip-sync global controls as CSV config.
   - Use a separate `lipsync_config_default_girl.csv`.
   - Keep `lipsync_visemes_default_girl.csv` as viseme weight data.
   - Candidate keys:
     - `LipSyncAlpha`
     - `JawScale`
     - `MouthOpenScale`
     - `SmoothingSpeed`
     - `AttackMs`
     - `ReleaseMs`
     - `SilenceGate`

6. Add viseme attack/release sampling.
   - Current point-in-time viseme application can look abrupt.
   - Use the config values above.
   - Verify in Unreal before changing ownership rules.

7. Defer mouth ownership resolver until visual evidence requires it.
   - Current `lip_sync_mask` is already a first ownership approximation.
   - Capture/inspect speaking frames first.
   - Only add phonetic/expressive/shared resolver if actual mouth conflict is visible.

### Explicit Non-Priority For The Next Step

Do not make SSE, WebSocket, DataAsset conversion, STT, VAD/EoT, ARKit/audio-to-face, or marker-based gesture timing the immediate next dependency.

Those are valid later phases, but they are not required to validate the next latency improvement.

## Current Status

### Server

Implemented:

- Runtime behavior provider structure.
- OpenAI runtime behavior provider.
- Mock/fallback runtime provider.
- Fast-path provider for common short conversational turns.
- Provider timeout and fallback handling.
- Emergency runtime fallback.
- Runtime session history.
- Character profile lookup.
- Latency metrics CSV logging.
- Azure TTS provider.
- Korean/English Azure voice selection.
- TTS fallback provider.
- TTS provider timeout and fallback timeout.
- Sync runtime API: `POST /api/runtime/respond`.
- Sync TTS API: `POST /api/runtime/tts/synthesize`.
- Runtime async job API: `POST /api/runtime/respond/async`, `GET /api/runtime/respond/jobs/{jobId}`.
- TTS async job API: `POST /api/runtime/tts/synthesize/async`, `GET /api/runtime/tts/jobs/{jobId}`.
- Turn-level async orchestration: `POST /api/runtime/turn/async`, `GET /api/runtime/turn/jobs/{turnJobId}`.
- Turn job stages: `pending` -> `responding` -> `synthesizing` -> `succeeded` / `failed`.
- Immediate reaction payload on turn job submit.
- Background job pruning, job task registry, job-level timeout, shutdown cancellation.
- Runtime audio WAV cleanup.
- SSE streaming endpoint: `POST /api/runtime/respond/stream`.
  - Emits `reaction` and `final` events.
  - Does not include `speechTimeline`.
  - TTS is not part of this stream.
- WebSocket endpoint: `ws://localhost:8010/ws/runtime`.
  - Emits `reaction` and `final` frames.
  - TTS is called separately after `final` arrives.
- Tests for async jobs, timeout, shutdown cancellation, TTS failure, job pruning, and audio cleanup.

Current turn-level flow:

```text
POST /api/runtime/turn/async
-> returns turnJobId + reaction immediately
-> server runs RuntimeCharacterService.respond()
-> server stores response
-> server runs TtsService.synthesize()
-> server stores speechTimeline

GET /api/runtime/turn/jobs/{turnJobId}
-> returns status
-> returns responseReady / ttsReady
-> returns response when ready
-> returns speechTimeline when ready
```

### Unreal Client

Implemented:

- `UPromptMotionRuntimeComponent`: main entry point, face blending, and TTS orchestration.
- `FPromptMotionApiClient`: async HTTP client for `/api/runtime/respond`.
- `FPromptMotionRealtimeClient`: WebSocket client for `/ws/runtime`.
- `FPromptMotionTtsClient`: TTS synthesize request, WAV download, and speech timeline parsing.
- `FFaceLipSyncLayer`: viseme-to-morph target weight application.
- `FFacePresetResolver`, `FPromptMotionFaceConfig`: CSV-driven face preset and viseme mapping.
- `FFaceMorphDomains`: morph target domain separation for expression vs lip-sync.
- Local immediate thinking face preset before HTTP request fires.
- Stale response guard using request IDs.
- Response behavior application to face presets.
- Speech timeline parsing and audio-time-driven lip-sync timeline playback.
- One Azure viseme ID can drive multiple morph targets.
- Face/lip-sync debug widget for PIE tuning.

Current Unreal HTTP flow, which is the active path:

```text
SendRuntimeMessage()
-> local thinking face preset
-> POST /api/runtime/respond
-> wait for final LLM response
-> apply final behavior / face preset
-> POST /api/runtime/tts/synthesize
-> wait for full TTS result
-> download WAV
-> play audio
-> drive lip-sync from SpeechTimeline via audio playback time
```

Current Unreal WebSocket flow, optional with `bUseRealtimeWebSocket = true`:

```text
SendRuntimeMessage()
-> local thinking face preset
-> send JSON over WebSocket
<- receive "reaction" frame -> apply thinking behavior immediately
<- receive "final" frame -> apply final behavior
-> POST /api/runtime/tts/synthesize
-> wait for full TTS result
-> download WAV
-> play audio
-> drive lip-sync from SpeechTimeline
```

The WebSocket path reduces visible reaction latency because the server can send a `reaction` frame before `final`.

It does not remove final reply latency. The `final` frame still waits for the LLM response. TTS is still a separate HTTP call made after `final` arrives. This means even with WebSocket enabled, the user still waits for:

```text
LLM final latency + TTS latency + WAV download time
```

before hearing audio.

Key mismatch:

- Server has `turn/async` with TTS included in the same job.
- Unreal still fires two separate completion-based HTTP calls.
- The server async infrastructure is currently unused by the client.

## Realtime Feel - Cold Assessment

### Current Integrated Feel

Score: 45-55 / 100

- The character applies a local thinking face preset immediately.
- Unreal then waits for `/api/runtime/respond`.
- Unreal then waits for `/api/runtime/tts/synthesize`.
- Audio does not start until both complete and WAV download finishes.
- This feels like a chatbot with face animation, not fully realtime conversation.
- The server async architecture exists, but the client integration does not use it yet.

### Expected After Connecting Unreal to `turn/async`

Score: 65-72 / 100

- One job per turn.
- Immediate server reaction applies on submit.
- Unreal polls response and TTS readiness independently.
- No double completion-based HTTP chain.
- Still polling-based, so perceived latency is not fully smooth.

### Expected After `turn/stream` SSE

Score: 75-82 / 100

- Server pushes each stage as it completes.
- No polling overhead.
- Client applies face and audio state as soon as each event arrives.
- Still whole-reply TTS, so long answers remain noticeable.

### Expected After Segment-Level TTS

Score: 85+ / 100

- First sentence audio starts before the full reply finishes synthesizing.
- This is the main perceptual threshold for "realtime dialogue" vs "chatbot with voice".
- Requires sentence segmentation on the server, sequential audio queueing in Unreal, and viseme timeline stitching per segment.

## Gaps

### Gap 1 - Unreal Is Not Using `turn/async`

Impact: critical

The server has a complete turn-level async API with TTS included. Unreal ignores it and still fires two sequential completion-based HTTP calls.

What Unreal needs:

- Submit: `POST /api/runtime/turn/async` -> get `turnJobId` + `reaction` immediately.
- Apply reaction face preset without waiting for polling.
- Poll: `GET /api/runtime/turn/jobs/{turnJobId}` at roughly 200ms interval.
- When `responseReady = true`: apply final behavior / face preset.
- When `ttsReady = true`: download and play audio, start lip-sync from `speechTimeline`.

Until this is done, the server-side async work has no visible effect on the user.

### Gap 2 - No `turn/stream` SSE Endpoint

Impact: high

A partial SSE endpoint exists at `POST /api/runtime/respond/stream`. It emits `reaction` and `final`, but does not include `speechTimeline`. TTS is not wired into the stream path.

What is needed:

```text
POST /api/runtime/turn/stream

event: reaction       -> immediate face preset
event: response       -> final text + behavior
event: speechTimeline -> viseme data + WAV URL
event: done
event: error
```

Once `turn/stream` exists, the `turn/async` polling path becomes a fallback, not the primary path.

### Gap 3 - TTS Is Whole-Reply

Impact: high

Current TTS waits for the full reply text before generating any audio. For long replies, this creates noticeable silence after the character's face changes.

What is needed:

- Server splits reply into short segments.
- TTS is generated per segment, first segment first.
- Server streams each segment's WAV URL + viseme data as it becomes ready.
- Unreal queues segment audio playback and starts the first segment immediately.
- Lip-sync timelines are stitched per segment using segment start offsets.

This is the single largest improvement to perceived naturalness after Gap 1 is fixed.

### Gap 4 - No Barge-In / Cancel

Impact: medium-high

If the user sends a new message while TTS is still playing, the old audio can continue until the client stops it. Client-side stale guards help, but server jobs are not explicitly cancelled by request.

What is needed on the server:

- `POST /api/runtime/turn/jobs/{turnJobId}/cancel`.
- Cancel pending respond/TTS tasks.
- Mark job as cancelled.

What is needed on Unreal:

- Cancel in-flight HTTP requests.
- Stop `USoundWaveProcedural` playback immediately.
- Reset `FFaceLipSyncLayer` weights to neutral.

Note: `CancelActiveTts()` already exists in `UPromptMotionRuntimeComponent` and handles audio + lip-sync reset. Missing pieces are in-flight HTTP request cancellation and the server-side cancel endpoint.

### Gap 5 - STT Not Implemented

Impact: medium-high for the "realtime conversation" claim

The current pipeline requires text input. There is no voice input path.

`STT-INPUT-REACTION-TIMELINE-PLAN.md` has a design for:

```text
push-to-talk -> partial reactions -> final STT text
```

None of this is implemented on server or client.

For the demo to feel like realtime conversation rather than chatbot-with-face, STT is eventually necessary. Recommended minimum is push-to-talk STT before VAD/EoT.

### Gap 6 - Azure Viseme Callback Not Guarded

Impact: medium

A malformed or unexpected viseme event from the Azure SDK should not break synthesis.

Fix:

- Wrap the viseme callback body with `try/except`.
- Skip malformed events.
- Log at warning level.

### Gap 7 - Env Parsing Not Hardened

Impact: medium

Several settings still use direct casts:

```python
float(os.getenv(...))
int(os.getenv(...))
```

A misconfigured env var can raise at startup.

Fix:

- Add typed env helpers:
  - `get_float_env(name, default, min_value, max_value)`
  - `get_int_env(name, default, min_value, max_value)`
- Log invalid values and use defaults.

### Gap 8 - Metrics Are Not Turn-Level

Impact: medium

Current metrics log runtime response latency. Realtime conversation needs turn-level breakdown:

- `reaction_ready_ms`
- `response_ready_ms`
- `tts_ready_ms`
- `audio_started_ms`
- `first_viseme_applied_ms`

Without this, it is hard to identify which stage is the bottleneck.

### Gap 9 - Health Check Is Too Basic

Impact: low-medium

`/health` only returns `{"status": "ok"}`.

Useful additions:

- OpenAI key configured.
- Azure key/region configured.
- Audio directory writable.
- Provider mode.
- Job store size.

## Deferred By Design

The following items are not current gaps. They are intentionally out of scope for the face-only MVP.

| Item | Status |
|---|---|
| `gestureKey` animation | Deferred. Parsed and stored but not acted on. No AnimBP wiring. No montage calls. |
| `headMotion` | Deferred. Same reason. |
| `gaze` IK / bone targeting | Deferred. The field is returned but no IK or aim offset is connected. |
| Body/full-body animation | Out of scope for realtime conversation phase. |
| ElevenLabs TTS | Deferred pending Azure baseline quality assessment. |
| Audio2Face | Not in scope for MVP. Too much infrastructure dependency. |
| VAD / EoT | Deferred. Push-to-talk comes first if STT is added. |
| Multi-agent conversation | Out of scope. |
| Redis job store | Not needed until multi-worker deployment. |

## Recommended Next Work

### Phase 1 - Connect Unreal to `turn/async`

Do this first. The server is ready. This is primarily a client-side change.

Tasks:

1. Add `FPromptMotionTurnAsyncClient` or extend `FPromptMotionApiClient` with turn async methods.
2. Replace current HTTP respond + sync TTS chain in `UPromptMotionRuntimeComponent`.
3. Apply `reaction` behavior immediately on job submit response.
4. Poll `turn/jobs/{id}` at roughly 200ms.
5. Apply face preset when `responseReady`.
6. Download WAV and start lip-sync when `ttsReady`.
7. Cancel previous turn polling + audio when a new message is sent.

Expected result:

- Server-side async work becomes visible.
- The character no longer waits through both LLM and TTS before audio behavior begins.

### Phase 2 - Add `turn/stream` SSE On Server

The existing `respond/stream` is only a starting point and does not include TTS.

Tasks:

1. Add `POST /api/runtime/turn/stream`.
2. Emit `reaction` -> `response` -> `speechTimeline` -> `done` / `error`.
3. Run respond + TTS inline in the generator or reuse the turn orchestrator.
4. Add server tests for event order and TTS failure.
5. Update Unreal to consume SSE instead of polling.

Expected result:

- No polling overhead.
- Client reacts to each stage as soon as it is ready.

### Phase 3 - Segment-Level TTS

Tasks:

1. Server splits reply into sentence-level segments.
2. Generate TTS per segment sequentially.
3. Stream each segment's WAV URL + viseme timeline via SSE.
4. Unreal queues audio and plays segment N while segment N+1 is synthesizing.
5. Lip-sync offsets each segment's viseme timeline by cumulative audio duration.

Expected result:

- Audio starts after first segment latency, not full-reply TTS latency.
- This is the biggest single jump in perceived naturalness.

### Phase 4 - STT Push-To-Talk Minimum

Tasks:

1. Unreal records microphone audio while a button is held.
2. Unreal sends WAV or stream to server.
3. Server adds `POST /api/runtime/stt/transcribe`.
4. Server returns transcribed text.
5. Unreal feeds the text into the existing turn flow.
6. Measure full latency from voice release to audio start.

Do not add VAD or EoT at this stage. Push-to-talk is enough to measure and demo the full voice pipeline.

### Phase 5 - Production Hardening

Tasks:

1. Guard Azure viseme callback with `try/except`.
2. Add env parsing helpers with defaults and clamping.
3. Add `/health/runtime`.
4. Add turn-level latency metrics.
5. Add server-side cancel endpoint.
6. Add Unreal in-flight HTTP request cancellation.

## MVP Verdict

Server-side async pipeline:

- Complete for polling-based flow.
- SSE turn stream is missing.

End-to-end realtime feel:

- Not achieved yet.

The specific reason:

- Unreal still fires two sequential completion-based HTTP calls.
- The async server infrastructure exists but is not yet connected to the client.

Connecting Unreal to `turn/async` should raise the current integrated feel from roughly 45-55 to roughly 65-72.

The project is past the "will this architecture work?" question. The current question is how quickly the client integration can catch up to the server.
