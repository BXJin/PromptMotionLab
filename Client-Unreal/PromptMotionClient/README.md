# PromptMotionClient

Unreal Engine 5 client for the realtime 3D AI character demo.

The client is responsible for immediate local character feedback, voice capture,
runtime server calls, TTS segment playback, expression blending, and lip-sync
morph application. The server decides high-level behavior; Unreal executes it
with cached local presets so the character does not freeze while external APIs
are running.

```text
PTT / voice capture
-> streaming STT or batch STT fallback
-> async runtime turn request
-> local thinking/listening expression
-> final Behavior JSON
-> face preset blend + gesture/gaze
-> TTS segment playback + viseme lip-sync
```

## Open Project

```text
Client-Unreal/PromptMotionClient/PromptMotionClient.uproject
```

Current default map:

```text
/Game/Map/ChildRoom
```

## Runtime Configuration

Main config:

| File | Role |
| --- | --- |
| [`Config/DefaultGame.ini`](Config/DefaultGame.ini) | Active runtime profile, local/production server URLs, async/streaming flags |
| [`Config/DefaultEngine.ini`](Config/DefaultEngine.ini) | Android/app/runtime engine settings |
| [`Config/DefaultInput.ini`](Config/DefaultInput.ini) | Input settings and mobile touch interface behavior |
| [`Config/PromptMotion`](Config/PromptMotion) | Face/lip-sync CSV mappings staged for runtime use |

Important values:

```ini
[PromptMotion.Runtime]
ActiveProfile=Local

[PromptMotion.Runtime.Local]
ServerUrl="http://localhost:8010"
StreamingSttWebSocketUrl="ws://127.0.0.1:8010/ws/stt"
bUseAsyncTurnHttp=true
bEnableStreamingStt=true
AsyncTurnPollIntervalSeconds=0.08
```

For packaged Android production builds, switch `ActiveProfile` to `Production`
or override the runtime profile before packaging.

## Key Code

### Runtime Orchestration

| File | Role |
| --- | --- |
| [`Source/PromptMotionClient/Runtime/Core/PromptMotionRuntimeComponent.h`](Source/PromptMotionClient/Runtime/Core/PromptMotionRuntimeComponent.h) | Main component that coordinates requests, behavior application, idle state, and debug commands |
| [`Source/PromptMotionClient/Runtime/Core/PromptMotionRuntimeComponent.cpp`](Source/PromptMotionClient/Runtime/Core/PromptMotionRuntimeComponent.cpp) | Async turn flow, stale response handling, face preset application, local fallback reactions |
| [`Source/PromptMotionClient/Runtime/Core/PromptMotionTypes.h`](Source/PromptMotionClient/Runtime/Core/PromptMotionTypes.h) | Runtime DTOs for behavior, speech timeline, and API responses |

### Server Communication

| File | Role |
| --- | --- |
| [`Source/PromptMotionClient/Runtime/Core/PromptMotionApiClient.h`](Source/PromptMotionClient/Runtime/Core/PromptMotionApiClient.h) | HTTP client for runtime turn, TTS, STT, and polling |
| [`Source/PromptMotionClient/Runtime/Core/PromptMotionRealtimeClient.h`](Source/PromptMotionClient/Runtime/Core/PromptMotionRealtimeClient.h) | Runtime WebSocket client |
| [`Source/PromptMotionClient/Runtime/Core/PromptMotionRuntimeEndpointConfig.h`](Source/PromptMotionClient/Runtime/Core/PromptMotionRuntimeEndpointConfig.h) | Loads active local/production endpoint settings |

### Voice Input And STT

| File | Role |
| --- | --- |
| [`Source/PromptMotionClient/Runtime/Core/PromptMotionVoiceInputController.h`](Source/PromptMotionClient/Runtime/Core/PromptMotionVoiceInputController.h) | Push-to-talk voice capture state machine |
| [`Source/PromptMotionClient/Runtime/Core/PromptMotionStreamingSttClient.h`](Source/PromptMotionClient/Runtime/Core/PromptMotionStreamingSttClient.h) | WebSocket streaming STT client |
| [`Source/PromptMotionClient/Runtime/Core/PromptMotionSttClient.h`](Source/PromptMotionClient/Runtime/Core/PromptMotionSttClient.h) | Batch STT fallback/debug client |

Expected streaming logs:

```text
[RuntimeConfig] ... streamingStt=true turnPoll=80ms
[STT] Streaming WebSocket connected: ws://127.0.0.1:8010/ws/stt
[VoiceLatency] ptt_stop ... streaming=true
[STT] Streaming final: "..."
```

### TTS And Audio Playback

| File | Role |
| --- | --- |
| [`Source/PromptMotionClient/Runtime/Core/PromptMotionTtsClient.h`](Source/PromptMotionClient/Runtime/Core/PromptMotionTtsClient.h) | TTS HTTP client |
| [`Source/PromptMotionClient/Runtime/Core/PromptMotionSpeechPlaybackController.h`](Source/PromptMotionClient/Runtime/Core/PromptMotionSpeechPlaybackController.h) | TTS segment queue, audio playback, lip-sync timeline dispatch |
| [`Source/PromptMotionClient/Runtime/Core/PromptMotionLatencyLogger.h`](Source/PromptMotionClient/Runtime/Core/PromptMotionLatencyLogger.h) | Local latency CSV/log helper |

### Face And Lip-Sync

| File | Role |
| --- | --- |
| [`Source/PromptMotionClient/Runtime/Face/FacePresetResolver.h`](Source/PromptMotionClient/Runtime/Face/FacePresetResolver.h) | Maps behavior emotion to local morph target preset weights |
| [`Source/PromptMotionClient/Runtime/Face/FaceLipSyncLayer.h`](Source/PromptMotionClient/Runtime/Face/FaceLipSyncLayer.h) | Applies viseme weights during TTS playback |
| [`Source/PromptMotionClient/Runtime/Face/FaceSpeechMicroLayer.h`](Source/PromptMotionClient/Runtime/Face/FaceSpeechMicroLayer.h) | Small speech-related expression modulation |
| [`Source/PromptMotionClient/Runtime/Face/FaceIdleLayer.h`](Source/PromptMotionClient/Runtime/Face/FaceIdleLayer.h) | Idle face motion layer |
| [`Source/PromptMotionClient/Runtime/Face/FaceMorphDomains.h`](Source/PromptMotionClient/Runtime/Face/FaceMorphDomains.h) | Separates expression/lip-sync/idle morph ownership |
| [`Source/PromptMotionClient/Runtime/Face/PromptMotionFaceConfig.h`](Source/PromptMotionClient/Runtime/Face/PromptMotionFaceConfig.h) | CSV path and face mapping loader |

### UI

| File | Role |
| --- | --- |
| [`Source/PromptMotionClient/Runtime/UI/PromptMotionInputWidget.h`](Source/PromptMotionClient/Runtime/UI/PromptMotionInputWidget.h) | Runtime input widget and profile selection |
| [`Source/PromptMotionClient/Runtime/UI/PromptMotionFaceDebugWidget.h`](Source/PromptMotionClient/Runtime/UI/PromptMotionFaceDebugWidget.h) | Face preset debug/edit widget |

## Design Choices

| Choice | Reason |
| --- | --- |
| Behavior JSON instead of raw morph arrays | Keeps server response compact and lets Unreal own animation quality |
| Async turn job | First visible reaction can start before final TTS is ready |
| 80ms async turn polling | Reduces worst-case wait after server-side TTS segment readiness compared with the older 200ms poll |
| Streaming STT | Reduces delay after PTT stop compared with batch WAV upload |
| Local face/lip-sync CSV mappings | Character-specific tuning without changing server contracts |
| Request ids and stale response checks | Prevents older responses from overwriting newer turns |

## Useful Checks

When testing PIE or Android quick launch, check these logs:

```text
[RuntimeConfig] profile=...
[VoiceLatency] stt_final ...
[VoiceLatency] llm_ready ...
[VoiceLatency] tts_ready ...
[VoiceLatency] audio_start ...
[PromptMotion] FacePreset blend started ...
[TTS] LipSync timeline started ...
```

If `provider=OpenAiSttProvider/gpt-4o-mini-transcribe` appears during a normal
PTT test, that turn used batch STT. For streaming STT, the provider should be
`AzureSpeechStreamingSttProvider` and `ptt_stop` should show `streaming=true`.
