# Runtime AI Character Agent Plan

Updated: 2026-05-15

## Purpose

This is the primary implementation path for PromptMotionLab.

The goal is a runtime 3D AI character that can respond to a user with low perceived latency by combining LLM/RAG output, Behavior JSON, TTS/lip-sync, facial presets, gaze, head motion, and short gesture playback in Unreal.

This plan is separate from text-to-motion. Text-to-motion is a later motion authoring pipeline, not the live conversation path.

## Core Principle

```text
LLM = 판단자
Behavior Planner = 번역기 / 스케줄러
Unreal = 실시간 실행자
```

The LLM should decide:

- answer text
- intent
- emotion
- intensity
- confidence
- gesture key
- gaze target
- TTS style

The LLM should not generate:

- frame-by-frame facial curves
- raw morph target values
- raw bone transforms
- live full-body motion
- viseme sequences
- hand/finger rotations

## Runtime Pipeline

```text
User Voice/Text
-> STT partial reaction, if voice input
-> final STT or text input
-> LLM / RAG / Memory
-> Behavior JSON
-> Behavior Planner
-> TTS / Speech Timeline
-> Lip-sync / viseme timeline
-> Unreal Runtime Character Controller
-> facial preset + gaze + blink + head + gesture
```

## Behavior JSON

Recommended MVP shape:

```json
{
  "reply": "제가 보기에는 이 전시물의 핵심은 움직임을 통해 감정을 전달한다는 점이에요.",
  "behavior": {
    "emotion": "friendly",
    "intensity": 0.58,
    "confidence": 0.84,
    "intent": "explain",
    "gaze": "user",
    "gestureKey": "explain_small",
    "headMotion": "small_nod",
    "ttsStyle": "warm"
  }
}
```

Segmented response can be added after the basic contract is stable:

```json
{
  "reply": "...",
  "segments": [
    {
      "text": "먼저 핵심부터 말하면,",
      "emotion": "thinking",
      "intensity": 0.45,
      "gestureKey": "small_ack"
    },
    {
      "text": "이 시스템은 실시간 모션 생성보다 안정적인 반응 제어가 중요합니다.",
      "emotion": "confident",
      "intensity": 0.65,
      "gestureKey": "explain_small"
    }
  ]
}
```

## STT Input Reaction Timeline

When the user speaks by voice, the runtime should distinguish partial STT reactions from final answer generation.

```text
Partial STT / pause / filler
-> Input Reaction Planner
-> Listening Timeline
-> face preset + gaze + blink + head motion

Final STT text
-> cleanup / question extraction
-> LLM answer
-> Behavior JSON + Speech Timeline
```

Example:

```text
Raw user speech:
음... 어.. 아! 맞다 그거였지 그 뭐야 그 덤블링! 그거 어떻게 하는거야?

Listening reactions:
음...   -> Thinking, gaze down_left
어..    -> Uncertain, small head tilt
아!     -> Surprised / realization
그 뭐야 -> Thinking / word search

Final answer target:
덤블링 어떻게 하는거야?
```

Core rule:

```text
Partial STT = listening reactions only
Final STT = answer generation
```

See `STT-INPUT-REACTION-TIMELINE-PLAN.md` for the detailed contract.

## Unreal Runtime Layers

```text
UPromptMotionRuntimeComponent
  - receives Behavior JSON / Speech Timeline
  - validates behavior keys against CharacterCapability
  - schedules segment timing
  - applies runtime layers

UCharacterExpressionAdapter
  - face preset -> morph target weights
  - intensity and CharacterProfile multipliers

UCharacterLipSyncAdapter
  - viseme/lip-sync timing -> jaw and mouth morphs

UCharacterGazeAdapter
  - gaze target -> eye/head control

UCharacterGestureAdapter
  - gesture key -> montage or Control Rig action
```

## Face Preset Strategy

Initial presets:

- neutral
- friendly
- happy
- thinking
- curious
- concerned
- uncertain
- apologetic

Final facial value should be computed in Unreal:

```text
final face =
neutral
+ face preset * emotion intensity * character multiplier
+ lip-sync layer
+ blink / gaze / head micro motion
```

Mouth conflict rule:

- lip-sync owns jaw open, mouth open/close, viseme shapes
- emotion owns eyes, brows, cheeks, and mouth corners
- conflict resolver blends mouth corners with speech mouth movement

## Low-Latency UX

The system should not wait for the full LLM answer before animating.

```text
0.0s user finishes input
0.1s character looks at user
0.2s thinking/listening preset starts
LLM first segment arrives
TTS starts for first sentence
lip-sync begins with audio
gesture key plays at segment boundary
```

This is perceived latency reduction, not true zero-latency generation.

## CharacterProfile

CharacterProfile controls how the same behavior appears on different characters:

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

## Runtime MVP Scope

Phase 1:

- one character
- mock or API LLM
- Behavior JSON schema
- facial preset preview
- gaze/head/blink
- TTS audio playback
- lip-sync/viseme mapping
- five short gestures

Phase 2:

- CharacterProfile
- domain RAG
- speech segment timing
- fallback behavior when LLM/TTS is slow

Phase 3:

- local LLM provider for intent/emotion/fallback
- local or hybrid STT/TTS experiments
- edge kiosk deployment path

## Text-to-Motion Boundary

Text-to-motion belongs to `../20-MotionAuthoring`.

Runtime should use:

```text
Behavior JSON -> gestureKey -> existing montage / Control Rig action
```

Later authoring can use:

```text
Prompt -> T2M/MDM/MotionGPT -> generated asset -> import/retarget/validate/bake -> gesture library
```

Do not make runtime conversation depend on live full-body motion generation.
