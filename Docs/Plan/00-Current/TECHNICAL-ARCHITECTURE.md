# TECHNICAL-ARCHITECTURE - PromptMotionLab

Updated: 2026-05-15

## 0. Architecture Decision

PromptMotionLab is designed around two separate pipelines.

Priority 1 is the **Runtime AI Character Control Pipeline**.

Later work is the **Motion Authoring / Text-to-Motion Pipeline**.

The runtime pipeline must not depend on live text-to-motion generation. Runtime character response should be driven by Behavior JSON, Speech Timeline, predefined facial presets, lip-sync, gaze, head motion, and short gesture playback.

```text
Priority 1:
User Voice/Text
-> STT partial listening reaction, if voice input
-> AI Server
-> LLM / RAG / Memory
-> Behavior JSON + Speech Timeline
-> Unreal Runtime Character Controller
-> facial preset + gaze + blink + head + lip sync + short gesture

Later:
Prompt
-> Text-to-Motion Provider / Motion Model
-> FBX/BVH/AnimSequence
-> import / retarget / validate / bake
-> runtime gesture library
```

## 1. Runtime System Overview

```text
[User Voice/Text]
        |
        v
[Input Reaction Planner - STT partial only]
        |
        | listening expression / gaze / head motion
        v
[Runtime Listening Timeline]
        |
        v
[AI Server - FastAPI]
        |
        | 1. conversation answer
        | 2. emotion / intent / confidence
        | 3. gesture key / gaze / speech style
        v
[Behavior JSON + Speech Timeline]
        |
        v
[Unreal Runtime Client]
        |
        +--> Face Preset Layer
        +--> LipSync / Viseme Layer
        +--> Gaze Layer
        +--> Blink / Idle Layer
        +--> Head Motion Layer
        +--> Gesture Montage / Control Rig Layer
```

Core rule:

```text
LLM = decides meaning and behavior intent
Behavior Planner = converts intent into a safe character timeline
Unreal = executes real-time animation layers
```

For voice input, partial STT should drive listening reactions only. The final STT text should drive answer generation.

The LLM should not output raw morph values, frame-by-frame facial curves, raw bone transforms, or live full-body motion.

## 2. AI Server

Recommended MVP stack:

```text
Python FastAPI
Pydantic v2
LLM provider interface
RAG provider interface
TTS provider interface
SQLite or local JSON logs
Local file storage for audio/cache
```

Future production stack:

```text
PostgreSQL
Redis queue
S3-compatible storage
Observability dashboard
Provider cost/latency logging
Optional local LLM worker
Optional local TTS/STT worker
```

### Server Responsibilities

- receive user text or final STT text
- optionally receive STT partial events for listening reaction planning
- run LLM / RAG / memory
- produce answer text
- produce Behavior JSON
- validate behavior schema
- create or request TTS audio
- collect viseme or lip-sync timing if provider supports it
- return Speech Timeline to Unreal
- provide fallback behavior when LLM/TTS is slow

### Runtime API Shape

```text
POST /api/conversation/respond
  body:
    {
      "sessionId": "session_001",
      "characterId": "calm_guide",
      "input": { "type": "text", "text": "이 전시물 설명해줘" },
      "context": { "locationId": "exhibit_01" }
    }

  response:
    {
      "reply": "...",
      "behavior": { ... },
      "speechTimeline": { ... }
    }
```

```text
POST /api/behavior/plan
  purpose:
    answer text and metadata -> behavior-only timeline
```

```text
POST /api/tts/synthesize
  purpose:
    text + ttsStyle -> audio + viseme timing
```

```text
GET /api/character/{characterId}/profile
  purpose:
    voice, expression, gaze, gesture, and safety style config
```

## 3. Behavior JSON Contract

MVP behavior should stay compact.

```json
{
  "reply": "트리케라톱스는 세 개의 뿔과 큰 프릴이 특징인 초식 공룡이에요.",
  "behavior": {
    "emotion": "friendly",
    "intensity": 0.6,
    "confidence": 0.9,
    "intent": "explain",
    "gaze": "user",
    "gestureKey": "explain_small",
    "headMotion": "small_nod",
    "ttsStyle": "warm"
  }
}
```

Do not use LLM-generated low-level morph values in MVP:

```json
{
  "Mouth_Smile_L": 0.62,
  "Mouth_Smile_R": 0.58,
  "Brow_Raise_Inner_L": 0.21,
  "Jaw_Open": 0.43
}
```

Low-level morph values belong in Unreal DataAssets/DataTables. The LLM chooses the behavior; Unreal applies the character-specific expression.

## 4. Speech Timeline Contract

Speech Timeline connects audio, viseme timing, expression timing, and gesture timing.

```json
{
  "utteranceId": "utt_001",
  "audio": {
    "url": "/api/audio/utt_001.wav",
    "durationSeconds": 3.2,
    "format": "wav"
  },
  "segments": [
    {
      "start": 0.0,
      "duration": 1.2,
      "text": "먼저 핵심부터 말하면,",
      "emotion": "thinking",
      "intensity": 0.45,
      "gaze": "down_left",
      "headMotion": "small_tilt",
      "gestureKey": "small_ack"
    }
  ],
  "visemes": [
    { "time": 0.12, "id": 1, "weight": 1.0 },
    { "time": 0.21, "id": 5, "weight": 1.0 }
  ]
}
```

## 5. Unreal Runtime Client

Recommended modules:

```text
PromptMotionRuntime/
  Core/
    PromptMotionRuntimeComponent
    BehaviorTimelinePlayer
    SpeechTimelinePlayer
  Character/
    CharacterProfile
    CharacterCapability
  Face/
    CharacterExpressionAdapter
    FacePresetDataAsset
    MorphTargetMapper
  Speech/
    CharacterLipSyncAdapter
    VisemeMapper
  Gaze/
    CharacterGazeAdapter
  Gesture/
    CharacterGestureAdapter
    GestureMontageRegistry
    ControlRigGestureDriver
  Network/
    PromptMotionApiClient
```

### Runtime Layer Responsibilities

| Layer | Responsibility |
|---|---|
| Face Preset | emotion preset, intensity, character style multiplier |
| LipSync / Viseme | jaw, mouth open/close, viseme morphs |
| Gaze | eye target, head look-at assist |
| Blink / Idle | always-on micro motion while waiting |
| Head Motion | nod, tilt, shake, listening/thinking motion |
| Gesture | short montage or Control Rig action selected by `gestureKey` |

### Mouth Conflict Rule

Lip-sync and emotion both affect the mouth, so they must be layered carefully.

```text
Emotion preset:
  eyes, brows, cheeks, mouth corners

Lip-sync:
  jaw open, mouth open/close, viseme shapes

Conflict resolver:
  preserve emotional mouth corners while lip-sync owns speech articulation
```

## 6. CharacterProfile

CharacterProfile lets the same Behavior JSON render differently per character.

```json
{
  "characterId": "calm_guide",
  "voiceId": "calm_female",
  "facialStyle": {
    "expressiveness": 0.55,
    "smileMultiplier": 0.65,
    "browMultiplier": 0.4,
    "transitionSpeed": 0.8,
    "talkMouthScale": 0.75,
    "blinkRate": 0.9,
    "gazeStability": 1.2
  },
  "gestureStyle": {
    "gestureScale": 0.6,
    "nodFrequency": 1.2,
    "handMotionScale": 0.5
  }
}
```

## 7. Low-Latency Strategy

Low latency is achieved by reducing generation work and running visible reactions before the full response is ready.

```text
0.0s user finishes input
0.1s Unreal starts listening/thinking expression
0.2s gaze/head idle continues
LLM first segment arrives
TTS starts for first sentence
lip-sync starts with audio
gesture plays at segment boundary
```

Key techniques:

- compact Behavior JSON
- streaming LLM response where possible
- sentence-level TTS queue
- immediate local listening/thinking fallback
- predefined facial presets
- predefined short gesture keys
- Unreal-side interpolation instead of LLM-generated curves

## 8. Text-to-Motion Boundary

Text-to-motion is explicitly out of the runtime MVP.

It belongs to `../20-MotionAuthoring`.

```text
Authoring path:
Prompt
-> provider/model generation
-> FBX/BVH/AnimSequence
-> import
-> retarget
-> validate
-> bake
-> gesture library

Runtime path:
Behavior JSON
-> gestureKey
-> stable montage / Control Rig action
```

This separation keeps the live conversation responsive and demo-safe.

## 9. Deployment Modes

| Mode | Description | Best For |
|---|---|---|
| Local kiosk | Unreal app runs on local PC, AI server local or cloud | exhibition MVP |
| Hybrid | Unreal local, LLM/TTS cloud, fallback behavior local | B2B pilot |
| Edge server | local server handles RAG/fallback for multiple kiosks | museum/showroom |
| Cloud rendering | Unreal runs on GPU server and streams video | web/mobile later |
| On-prem | local LLM/RAG/TTS for security-sensitive sites | enterprise later |

## 10. Success Criteria

- The architecture clearly separates runtime control from motion authoring.
- The live character can react immediately without waiting for full motion generation.
- LLM output remains compact and schema-valid.
- Unreal owns low-level animation execution.
- Text-to-motion can be added later without changing the runtime behavior contract.
