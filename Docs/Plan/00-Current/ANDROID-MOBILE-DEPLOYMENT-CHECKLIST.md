# Android Mobile Deployment Checklist

Last updated: 2026-05-25

## Current Status

- Android Development build now passes on this machine.
- APK generation completed through Gradle.
- Local SDK/NDK is pinned to an ASCII-only path because the NDK/Gradle toolchain fails or emits encoding errors when paths include the Korean Windows user profile name.

Local Android toolchain used:

- `C:/tmp/AndroidSdk`
- NDK `27.2.12479018` / r27c
- Android SDK Platform `android-35`
- Build Tools `35.0.0`

Verification command:

```powershell
& "C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" PromptMotionClient Android Development -Project="C:\Portfolio\PromptMotionLab\Client-Unreal\PromptMotionClient\PromptMotionClient.uproject" -WaitMutex -NoHotReload -NoLiveCoding
```

Known local warning:

- Gradle/AIDL may print `unmappable character ... UTF-8` because Gradle cache still lives under `C:\Users\<KoreanName>\.gradle`.
- The latest Development build still completed successfully despite those warnings.

## Implemented

- Android manifest permission:
  - `android.permission.RECORD_AUDIO`
- Runtime Android microphone permission request:
  - `RequestMicrophonePermission()`
  - Android permission callback updates `VoiceStatus`
- Voice input:
  - Push-to-talk
  - RMS VAD
  - TTS cooldown
  - barge-in cancel
  - STT latency trace
- Network resilience:
  - STT request timeout and one retry for network/408/429/5xx
  - TTS synth timeout and one retry for network/408/429/5xx
  - WAV download timeout and one retry for network/408/429/5xx
- Speech playback:
  - sentence-level TTS queue
  - first segment audio starts as soon as ready
  - segment lip-sync timeline handoff

## Device Test Pass Criteria

### Permission

- First app launch shows Android microphone permission prompt.
- If allowed:
  - voice status returns to `Idle` or `Listening`.
  - PTT and VAD can start capture.
- If denied:
  - voice status becomes `Error`.
  - app does not crash.
  - voice capture does not start.

### Push-To-Talk

- Hold/tap PTT begins capture.
- Release sends STT request.
- Empty/too-short audio does not send a request.
- Network failure returns to stable UI state after the error hold.

### VAD

- Quiet room does not auto-trigger.
- Normal speech starts capture within acceptable delay.
- End silence sends STT after configured silence window.
- TTS playback does not immediately retrigger VAD from speaker echo.

### Barge-In

- While character is speaking, user speech cancels current TTS.
- New STT request starts without leaving stale lip-sync morphs active.
- If speech is only speaker echo, cooldown suppresses it.

### Latency

Track from `Saved/Metrics/voice_latency_client.csv`:

- `speech_end_ms`
- `stt_ready_ms`
- `llm_ready_ms`
- `tts_ready_ms`
- `audio_play_start_ms`

Target for first production pass:

- PTT/VAD end to first audio: under 4 seconds on stable network.
- First visible reaction: immediate local `thinking` expression.
- No repeated `Error` states in normal Wi-Fi/LTE conditions.

## Azure Server Requirements

- UE app must call only the PromptMotion server, never OpenAI/Azure keys directly.
- Production server URL should use HTTPS.
- Server must keep provider keys in Azure environment variables or Key Vault.
- Audio files should eventually move from local disk serving to Blob Storage/CDN if traffic grows.
- Enable request limits and 429 responses server-side before public release.

## Play Store Readiness Gaps

Not solved yet:

- Real device microphone/VAD/echo test not run.
- Acoustic echo cancellation is not confirmed.
- Privacy policy text for microphone/audio processing is not written.
- Release signing, package name, versioning, and Play Console metadata are not configured.
- Current package name is still `com.YourCompany.PromptMotionClient`; this must be changed before Play Store upload.

## Next Engineering Steps

1. Set production Android package name, app label, version code, and release signing config.
2. Run Android release package/cook after package identity is fixed.
3. Test on one physical Android phone with logs open.
4. Tune:
   - `VadStartRmsThreshold`
   - `VadEndRmsThreshold`
   - `VadEndSilenceSeconds`
   - `VoiceTtsCooldownSeconds`
5. Add a production server URL config path for Azure deployment.
6. Draft privacy policy and in-app microphone usage wording.
