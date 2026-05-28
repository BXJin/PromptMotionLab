# Reference Avatar Runtime Analysis

Updated: 2026-05-21

## Purpose

This document analyzes reference projects and SDK designs that are relevant to PromptMotionLab's runtime character direction.

References reviewed:

- Local: `C:\dev\reference\promptMotion\unreal-audio2lipsync`
- Local: `C:\dev\reference\promptMotion\ai-iris-avatar`
- Local: `C:\dev\reference\promptMotion\TalkingHead3D`
- Official docs: Inworld Unreal Lip-sync and Inworld TTS timestamps

PromptMotionLab should not copy these projects as a whole. The useful part is the runtime design pattern:

```text
AI / TTS / audio timing
-> behavior or viseme timeline
-> renderer-side adapter
-> morph target / blendshape / LiveLink / animation layer
```

## Executive Summary

The references confirm that PromptMotionLab's current architecture is reasonable.

Important patterns found:

1. Use a character-specific data asset to map abstract visemes to morph targets.
2. Cache phoneme or viseme spans once per utterance, then sample by playback time every tick.
3. Keep lip-sync articulation and emotional mouth shape separate.
4. Put global lip-sync controls such as alpha, smoothing, gain, and silence gate in the runtime.
5. Queue speech, breaks, markers, and animations instead of treating speech as a single blocking action.
6. Measure time-to-first-audio, total TTS time, and LLM time separately.
7. Use idle micro motion, blink, gaze, breathing, and head movement to keep the character alive while waiting.
8. Treat web, Unity, Unreal, MetaHuman, and custom morph rigs as renderer adapters behind the same behavior contract.

Recommended PromptMotionLab action:

```text
Do now:
- Add/strengthen VisemeMappingDataAsset.
- Add LipSyncAlpha, JawScale, SmoothingSpeed, silence gate, fade in/out.
- Split mouth channels into phonetic and expressive ownership.
- Add runtime metrics: llm_ms, tts_first_audio_ms, tts_total_ms, audio_download_ms, playback_start_ms.
- Add speech queue items: audio, behavior segment, break, marker.

Do later:
- Test ARKit curve timeline support as an optional adapter.
- Add Web/VRM adapter only after Unreal runtime is stable.
- Consider ML audio-to-face only as a future provider, not MVP dependency.
```

## Fit Against PromptMotionLab

Current PromptMotionLab plan:

```text
LLM / RAG
-> Behavior JSON
-> Behavior Planner
-> Speech Timeline
-> Unreal Runtime Character Controller
-> face preset + gaze + blink + head + lip sync + gesture
```

Reference projects show adjacent approaches:

| Reference | Closest Match | Main Value | Reuse Level |
|---|---|---|---|
| Inworld Unreal Lip-sync | TTS timestamp -> viseme -> AnimGraph morph curves | Unreal lip-sync architecture | High as design reference |
| unreal-audio2lipsync | audio -> ARKit curves -> LiveLink MetaHuman | face timeline parsing, audio sync, mouth layer split | Medium, code reference possible |
| AI-Iris-Avatar | LLM/TTS server -> Unity client -> Oculus LipSync | latency measurement, WebSocket event flow, idle life layer | Medium as design reference, avoid code copy |
| TalkingHead3D | web TTS/viseme -> Three.js morphTargetInfluences | expression presets, speech queue, web adapter, viseme timing | High as concept reference |

## 1. Inworld Unreal Lip-sync

Sources:

- https://docs.inworld.ai/unreal-engine/runtime/inworld-lipsync
- https://docs.inworld.ai/tts/capabilities/timestamps

### Architecture

Inworld's lip-sync path is:

```text
TTS output
-> audio + word timestamps
-> word -> phones -> phoneme / viseme / timestamp
-> voice audio component playback
-> per-frame viseme blends
-> AnimGraph node
-> morph target curves
```

Relevant types from the official docs:

- `FInworldData_TTSOutput`: synthesized audio, text, timestamps.
- `FInworldAudioChunkTimestamp`: word token, start/end time, phone spans.
- `FInworldPhoneSpan`: phoneme, viseme category, timestamp, duration.
- `FInworldVisemeBlends`: blend weights for viseme categories.
- `UInworldVoiceAudioComponent`: owns playback and exposes playback events.
- `UInworldVisemeDataAsset`: maps viseme categories to morph target curve names and weights.
- `UAnimGraphNode_InworldViseme`: applies morph target curves from viseme blends.

### Strong Design Points

The best pattern is:

```text
OnVoiceAudioStart:
  flatten timestamps into cached phone spans

OnVoiceAudioPlayback every tick:
  current playback time
  -> GetVisemeBlends(cached phone spans)
  -> AnimBP variable
  -> AnimGraph viseme node
```

This avoids recalculating phoneme structures every frame.

Inworld also exposes:

```text
SmoothingSpeed
Alpha
VisemeDataAsset
```

These are exactly the controls PromptMotionLab needs because current logs suggest JawOpen and mouth strength are too high.

### PromptMotionLab Application

Add a PromptMotion lip-sync mapping asset:

```text
UPromptMotionVisemeMappingDataAsset
  VisemeEntries:
    - VisemeId / VisemeName
    - MorphTargetWeights: TMap<FName, float>
  Global:
    Alpha
    JawScale
    MouthOpenScale
    SmoothingSpeed
    SilenceGateThreshold
```

Runtime flow:

```text
SpeechTimeline.visemes
-> cache spans at utterance start
-> sample by AudioComponent playback time
-> produce current viseme blend
-> apply mapped morph targets
```

Use character-specific mapping instead of hardcoding `Jaw_Open` or `V_Open` in code.

Suggested first mapping direction:

```text
open vowel:
  V_Open: 0.45
  Jaw_Open: 0.25

bilabial / close:
  Mouth_Close: 0.70
  Jaw_Open: 0.00

rounded:
  V_Tight_O: 0.45
  Jaw_Open: 0.15

rest / silence:
  all viseme morphs: 0
```

### Caution

Inworld is an SDK/product reference, not an open-source base. Use the architecture and terminology as design reference, not code.

## 2. unreal-audio2lipsync

Local path:

```text
C:\dev\reference\promptMotion\unreal-audio2lipsync
```

License:

```text
MIT
```

### Structure

```text
python/
  src/
    server.py
    server_lipsync_face.py
    model.py
    constants.py
    prepare_data.py
    train.py
unreal/
  Source/Audio2Lipsync/
    Public/
      AudioImporterLib.h
      FaceAnimationLib.h
      LiveLinkFaceComponent.h
    Private/
      AudioImporterLib.cpp
      FaceAnimationLib.cpp
      LiveLinkFaceComponent.cpp
    ThirdParty/dr_mp3.h
    Audio2Lipsync.Build.cs
```

### Architecture

Standalone path:

```text
audio file / base64
-> Python FastAPI sidecar
-> HuBERT / Wav2Vec2 + Transformer
-> 52 ARKit mouth/jaw blendshape curves
-> JSON response with arkit_raw + audio_base64
-> Unreal C++ parser
-> LiveLink subject
-> MetaHuman face AnimBP
```

Merged path:

```text
audio -> LipSync model -> mouth / jaw / cheek / tongue
text prompt -> Text2Face -> brows / eyes / head
combine -> 61-channel ARKit timeline
```

This is not the same as PromptMotionLab. It generates low-level ARKit curves from audio and text. PromptMotionLab intentionally keeps the LLM at behavior level and lets Unreal own morph execution.

### Useful Files

```text
unreal/Source/Audio2Lipsync/Public/FaceAnimationLib.h
unreal/Source/Audio2Lipsync/Private/FaceAnimationLib.cpp
unreal/Source/Audio2Lipsync/Public/LiveLinkFaceComponent.h
unreal/Source/Audio2Lipsync/Private/LiveLinkFaceComponent.cpp
python/src/server.py
python/src/server_lipsync_face.py
python/src/constants.py
```

### Strong Design Points

#### Face Timeline Data Structure

`FFaceAnimationData` stores:

```text
ChannelNames
Frames as flat array
NumFrames
NumChannels
Duration
Fps
```

This is useful if PromptMotionLab later supports ARKit curve timelines or provider-generated facial curves.

Potential PromptMotion equivalent:

```text
FFaceCurveTimeline
  Channels: [Jaw_Open, V_Open, Mouth_Smile_L, ...]
  Frames: flat float array
  Fps
  DurationSeconds
  Source: AzureViseme / Audio2Face / ARKit / Debug
```

Do not make this the default MVP contract. Keep it as optional provider output.

#### Parser / Sampler Split

`FaceAnimationLib` separates:

```text
ParseFaceAnimJSON
SampleChannel
SampleAllChannels
ScaleChannels
BlendAnimations
```

This is a clean utility separation. PromptMotionLab should keep similar separation:

```text
SpeechTimelineParser
VisemeTimelineSampler
FacePresetSampler
LayerBlendResolver
```

#### Audio + Face Sync

`LiveLinkFaceComponent` starts audio and face animation together:

```text
PlayWithAudio(faceData, audio)
-> PlayAnimation(faceData)
-> AudioComponent.Play()
```

It samples all channels from elapsed time each tick and pushes a frame to LiveLink.

PromptMotionLab should ensure the authoritative clock is the audio playback clock when possible:

```text
AudioComponent playback time
-> sample visemes
-> sample expression segments
-> sample gaze/head/gesture segment state
```

If Unreal's current audio path cannot expose reliable playback time, keep the existing local elapsed-time clock but measure drift.

#### Job Cache

The Python server supports:

```text
POST /generate
POST /upload
GET /latest
GET /result/{job_id}
```

It stores generated results in an LRU cache.

PromptMotionLab can use the same idea for TTS:

```text
utteranceId -> audio file + speechTimeline
GET /api/runtime/audio/{utteranceId}.wav
GET /api/runtime/speech/{utteranceId}
```

This helps replay, debug, and avoid regenerating repeated demo phrases.

#### Tuning Controls

The server exposes:

```text
gain
smooth_window
silence_gate
silence_threshold_db
fade_in_ms
fade_out_ms
```

These are directly relevant to PromptMotionLab's current mouth problem.

Add runtime/provider settings:

```json
{
  "lipSync": {
    "alpha": 0.65,
    "jawScale": 0.45,
    "mouthOpenScale": 0.60,
    "smoothingSpeed": 10.0,
    "silenceGate": 0.35,
    "fadeInMs": 80,
    "fadeOutMs": 180
  }
}
```

#### Mouth Ownership Split

The most important idea is in `server_lipsync_face.py`.

It splits mouth curves into:

```text
LIPSYNC_PHONETIC:
  jaw, close, funnel, pucker, roll, press, tongue

EXPRESSIVE_MOUTH:
  smile, frown, dimple, stretch, cheek, upper/lower expression shapes
```

Blend modes:

```text
split:
  phonetic channels from lip-sync
  expressive channels additive with emotion

replace:
  all mouth channels from lip-sync

additive:
  all mouth channels additive, higher risk of exaggeration
```

PromptMotionLab should implement this as the default conflict resolver:

```text
LipSync owns:
  Jaw_Open
  Mouth_Close
  V_*
  phonetic tongue / rounded / bilabial shapes

Expression owns:
  Mouth_Smile_L/R
  Mouth_Frown_L/R
  Cheek_Raise
  Eye / Brow / Nose

Shared expressive mouth:
  additive, clamped, scaled by expressionIntensity
```

### What Not To Do

Do not switch PromptMotionLab MVP to ML audio-to-face.

Reasons:

- It adds model hosting and GPU dependency.
- It is MetaHuman/ARKit-oriented.
- It produces low-level curves, while PromptMotionLab's current product value is behavior-level runtime control.

Use it later as an optional provider:

```text
SpeechTimeline provider:
  Azure viseme timeline first
  Audio2Face / audio2lipsync provider later
```

## 3. AI-Iris-Avatar

Local path:

```text
C:\dev\reference\promptMotion\ai-iris-avatar
```

License:

```text
GPL-3.0
```

Do not copy code into PromptMotionLab unless the license implications are acceptable. Treat it as architecture reference.

### Structure

```text
server/
  app_logic.py
  socket_msg_handler.py
  server.py
  signal.py
  tts_utils.py
unity-project/
  Assets/Scripts/
    SpeechController.cs
    LipSyncCopyVisemes.cs
    BlinkController.cs
    EyesFollowCameraController.cs
    AnimationStateMachine.cs
    WebSocketClientBehaviour.cs
    WebSocketMsgHandler.cs
```

### Architecture

```text
Unity client
-> WebSocket query
-> Python server
-> local LLM via Ollama
-> TTS
-> WAV bytes streamed/sent to Unity
-> Unity schedules audio
-> Oculus LipSync derives visemes
-> SkinnedMeshRenderer blendshape weights
```

### Strong Design Points

#### Event Bus

`AppLogic` exposes event signals:

```text
on_query
on_text_response
on_tts_response
on_tts_timings
on_tts_first_chunk
on_play_vfx
```

`SocketMsgHandler` subscribes differently depending on whether the connection is Unity or browser UI.

PromptMotionLab can use the same idea on the server:

```text
RuntimeEvents:
  onUserInputReceived
  onLlmStarted
  onLlmCompleted
  onTtsFirstAudio
  onTtsCompleted
  onSpeechTimelineReady
```

This is useful for logs, debug panels, and later streaming.

#### Sentence-Level TTS

`AppLogic._exec_tts` splits response text into sentences and sends each TTS chunk as it becomes available.

PromptMotionLab should adopt the same direction:

```text
LLM reply segments
-> TTS sentence 1 starts
-> Unreal plays sentence 1
-> TTS sentence 2 is queued
```

This reduces perceived latency more than simply optimizing total TTS duration.

#### Time-To-First-Audio Metric

AI-Iris explicitly reports:

```text
elapsed_llm
first_chunk_tts
elapsed_tts
```

PromptMotionLab should log:

```text
request_started_ms
llm_completed_ms
tts_first_audio_ms
tts_timeline_ready_ms
audio_downloaded_ms
audio_play_started_ms
first_viseme_applied_ms
```

Current PromptMotion logs already show `server` and `llm`. Add the rest before optimizing blindly.

#### Speaking State Machine

Unity uses:

```text
HandleSendQuery -> IsSpeaking = true
HandleIsSpeakingChange(false) -> IsSpeaking = false
```

PromptMotionLab should map this into Unreal:

```text
User submits input:
  state = Thinking / PreparingToSpeak

Audio starts:
  state = Speaking

Audio queue empty:
  state = IdleListening
```

This avoids a dead-looking character during 4-5 second LLM latency.

#### Breathing / Idle Mouth

`SpeechController` runs breathing when not speaking and clears it when speech starts.

PromptMotionLab equivalent:

```text
Idle layer:
  subtle nostril / jaw / cheek / chest or head motion

Speaking starts:
  suspend mouth idle shapes
  keep blink / gaze / head micro motion
```

This helps avoid the face looking static while waiting.

#### Blink and Gaze Controllers

`BlinkController` has:

```text
random interval
blink duration
interpolation curves
brow/squint changes during blink
```

`EyesFollowCameraController` has:

```text
target tracking
min angle threshold
update interval
up/down/inside/outside constraints
```

PromptMotionLab should not implement gaze as a raw continuous look-at only. Add stability and thresholds:

```text
gazeTarget=user
gazeStability=1.2
minRetargetAngle=2 deg
retargetInterval=0.8-1.5s
eyeRotationLimits
```

### What To Borrow Conceptually

- WebSocket/event separation.
- Sentence-level TTS.
- Latency metrics.
- Speaking/idle state.
- Blink/gaze/breathing as always-on life layers.
- Audio delay control if lips appear late or early.

### What Not To Borrow

- Do not copy GPL C# code.
- Do not port Unity-specific animation code directly.
- Do not use Oculus LipSync as the primary Unreal path unless it is explicitly chosen later.

## 4. TalkingHead3D

Local path:

```text
C:\dev\reference\promptMotion\TalkingHead3D
```

License:

```text
MIT
```

### Structure

```text
modules/
  talkinghead.mjs
  lipsync-en.mjs
  lipsync-fi.mjs
  lipsync-lt.mjs
avatars/
animations/
poses/
examples/
index.html
```

### Architecture

```text
Text or external audio
-> TTS / audio buffer
-> word timestamps
-> viseme timings
-> speech queue
-> animation queue
-> Three.js morphTargetInfluences
```

TalkingHead3D is valuable because it shows a renderer-agnostic version of what PromptMotionLab wants:

```text
abstract expression / viseme / pose
-> renderer adapter
-> GLB morph targets and animation clips
```

### Strong Design Points

#### Mood Presets

`talkinghead.mjs` defines mood presets with:

```text
baseline morph values
speech modifiers
idle animations
talking animations
```

Example structure:

```text
neutral:
  baseline
  speech
  breathing
  pose
  head
  eyes
  blink
  mouth
  misc

happy / angry / sad / fear / disgust / love / sleep:
  same shape, different values and timings
```

PromptMotionLab should evolve `FacePreset` from only static morph values to:

```json
{
  "preset": "friendly",
  "baseline": {
    "Mouth_Smile_L": 0.25,
    "Cheek_Raise_L": 0.15
  },
  "speechStyle": {
    "rateDelta": 0.0,
    "pitchDelta": 0.1
  },
  "microMotions": {
    "blink": "...",
    "eyes": "...",
    "head": "...",
    "mouthIdle": "..."
  }
}
```

This would make expressions feel less flat than a one-time blend.

#### Speech Queue

TalkingHead3D supports queue items:

```text
text
audio
emoji
break
marker
anim
```

PromptMotionLab should introduce a speech queue:

```text
FSpeechQueueItem
  type: Audio | Break | Marker | BehaviorSegment
  startPolicy
  duration
  payload
```

Why this matters:

- TTS can stream sentence by sentence.
- Pauses can be explicit.
- Markers can trigger gaze, gesture, or UI events.
- The character can avoid hard stops between utterances.

#### Viseme Timing Shape

TalkingHead3D's external audio format accepts:

```text
words
wtimes
wdurations
visemes
vtimes
vdurations
markers
mtimes
```

This maps closely to PromptMotionLab:

```json
{
  "segments": [],
  "visemes": [],
  "markers": []
}
```

Add `markers` to `SpeechTimeline` later:

```json
{
  "time": 1.24,
  "name": "gesture.explain_small",
  "payload": { "intensity": 0.5 }
}
```

#### Viseme Attack / Hold / Release

When TalkingHead3D receives a viseme, it creates an animation with:

```text
attack before phoneme
peak near phoneme
release after phoneme
```

The exact implementation uses three timestamps around the viseme time.

PromptMotionLab should do the same instead of setting viseme morphs only at a point in time:

```text
viseme event at t, duration d
-> attack: t - min(60ms, 2d/3)
-> peak:   t + min(25ms, d/2)
-> release:t + d + min(60ms, d/2)
```

This will reduce robotic snapping.

#### Mood Affects Voice

TalkingHead3D mood presets include speech deltas:

```text
deltaRate
deltaPitch
deltaVolume
```

PromptMotionLab's `ttsStyle` can map to SSML:

```text
friendly -> warm, slightly brighter pitch
concerned -> slower, softer
thinking -> slower with pauses
excited -> faster, brighter
```

Do not let the LLM emit raw SSML. Let Behavior Planner map `ttsStyle` to provider-specific SSML.

#### Web Adapter Proof

TalkingHead3D uses Three.js and GLB/Ready Player Me morph targets. This supports PromptMotionLab's multi-renderer plan:

```text
Behavior JSON
-> Web Adapter
-> VRM / GLB expression names
-> morphTargetInfluences
```

Do not build this now, but keep Behavior JSON renderer-independent.

### Caution

TalkingHead3D is web-specific. Its animation queue is useful conceptually, but Unreal should implement equivalent logic with Unreal timers, components, AnimBP variables, and DataAssets.

## Recommended PromptMotionLab Design Updates

### 1. Add Viseme Mapping DataAsset

Current problem:

```text
JawOpen appears too strong.
Eye/brow expression appears weak.
```

Recommended Unreal asset:

```text
UPromptMotionVisemeMappingDataAsset
  Entries:
    VisemeKey
    MorphWeights
  Global:
    Alpha
    JawScale
    MouthOpenScale
    SmoothingSpeed
    AttackMs
    ReleaseMs
```

This should be per character, not global hardcoded logic.

### 2. Add Layer Ownership Rules

Implement a conflict resolver:

```text
LipSyncPhonetic:
  Jaw_Open
  Mouth_Close
  V_*
  tongue phonetic shapes

ExpressionMouth:
  Mouth_Smile_L/R
  Mouth_Frown_L/R
  Mouth_Dimple_L/R
  Mouth_Stretch_L/R
  Cheek_Raise_L/R

UpperFace:
  brow
  eye
  cheek
  nose

Idle:
  blink
  gaze micro motion
  subtle head
```

Default blend mode:

```text
phonetic channels: replace
expressive mouth: additive then clamp
upper face: expression preset owns
idle blink/gaze: independent
```

### 3. Add Speech Queue

Instead of treating a response as one monolithic playback:

```text
SpeechTimeline
-> SpeechQueue
   - behavior segment
   - audio segment
   - break
   - marker
```

MVP queue item:

```json
{
  "type": "audio",
  "utteranceId": "utt_001",
  "startTime": 0.0,
  "duration": 2.4,
  "behavior": {
    "emotion": "friendly",
    "gestureKey": "small_ack"
  }
}
```

### 4. Add Markers

Speech markers can trigger non-lip behaviors:

```json
{
  "markers": [
    { "time": 0.4, "name": "gaze.user" },
    { "time": 1.1, "name": "gesture.explain_small" },
    { "time": 1.8, "name": "head.small_nod" }
  ]
}
```

This avoids forcing all behaviors into `segments`.

### 5. Add Runtime Metrics

Required logs:

```text
input_received_ms
request_sent_ms
llm_first_token_ms
llm_complete_ms
tts_first_audio_ms
tts_complete_ms
speech_timeline_ready_ms
audio_download_complete_ms
audio_play_start_ms
first_viseme_applied_ms
audio_play_complete_ms
```

This will make latency work factual.

### 6. Improve Idle Life Layer

Add always-on components:

```text
BlinkController
GazeController
HeadIdleController
BreathingOrSubtleFaceController
ListeningReactionController
```

Important rules:

- Blink should continue during thinking and speaking.
- Gaze should be stable, not constantly locked to target.
- Mouth idle should stop or reduce during lip-sync.
- Speaking should trigger small head motion even before audio starts.

### 7. Keep Behavior JSON High-Level

References confirm the current rule:

```text
LLM should not output raw morph values.
```

Keep:

```json
{
  "emotion": "friendly",
  "intensity": 0.6,
  "gestureKey": "explain_small",
  "gaze": "user",
  "ttsStyle": "warm"
}
```

Avoid:

```json
{
  "Jaw_Open": 0.73,
  "Mouth_Smile_L": 0.22
}
```

Renderer adapters and character assets should own raw values.

## Implementation Priority

### Phase A - Immediate Tuning

1. Add `LipSyncAlpha`, `JawScale`, `MouthOpenScale`.
2. Reduce `Jaw_Open` and `V_Open` defaults.
3. Add smoothing and attack/release around viseme events.
4. Strengthen brow/eye values in `thinking`, `concerned`, `curious`.
5. Add logs for first TTS/audio/viseme timing.

### Phase B - Architecture Cleanup

1. Create `VisemeMappingDataAsset`.
2. Move hardcoded morph mappings into DataAssets.
3. Add layer ownership resolver.
4. Add speech queue and markers.
5. Add per-character `CharacterProfile` multipliers.

### Phase C - Optional Provider Experiments

1. ARKit curve timeline adapter.
2. Audio-to-face provider adapter.
3. Web/VRM renderer adapter.
4. Local TTS/lip-sync experiments.

## Reuse Decision

| Item | Reuse Type | Decision |
|---|---|---|
| Inworld VisemeDataAsset pattern | Design | Adopt |
| Inworld playback-time sampling | Design | Adopt |
| unreal-audio2lipsync FaceAnimationData | Design/code reference | Optional later |
| unreal-audio2lipsync LiveLink path | Code reference | Only for MetaHuman adapter |
| unreal-audio2lipsync mouth split | Design | Adopt soon |
| AI-Iris WebSocket event flow | Design | Adopt concept |
| AI-Iris sentence TTS | Design | Adopt soon |
| AI-Iris Unity C# code | Code | Do not copy due GPL |
| TalkingHead3D mood presets | Design | Adopt concept |
| TalkingHead3D speech queue | Design | Adopt |
| TalkingHead3D viseme attack/release | Design | Adopt |
| TalkingHead3D web adapter | Future reference | Later |

## Final Judgment

PromptMotionLab should stay on its current path.

The references do not show a better single architecture to replace it. They show that PromptMotionLab should become more explicit about:

- character-specific viseme mapping
- speech queueing
- mouth conflict resolution
- idle life layers
- metrics-driven latency tuning
- renderer adapters

The strongest immediate improvement is not a new model or new SDK. It is runtime control quality:

```text
Behavior JSON remains high-level.
Unreal owns morph execution.
Viseme mapping becomes data-driven.
Lip-sync and emotional mouth are layered deliberately.
Speech/TTS playback becomes queued and measurable.
```
