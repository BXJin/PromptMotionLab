# MVP-PLAN - PromptMotionLab

Updated: 2026-05-14

## MVP Definition

The MVP is a **runtime AI character control system**.

It converts an AI response into a compact behavior contract and lets Unreal execute the character performance in real time.

```text
User Prompt / Voice
-> LLM Answer
-> Behavior JSON / Speech Timeline
-> Unreal Runtime Character Controller
-> facial expression + gaze + blink + head motion + lip sync + short gesture
```

The MVP is not a runtime full-body text-to-motion system.

## MVP Goal

Prove that one character can answer a user while showing the answer's intent, emotion, and confidence through:

- facial preset blending
- gaze direction
- blink and idle motion
- head nod/tilt
- TTS audio
- viseme/lip-sync
- short gesture keys

The target experience is "responsive and expressive", not "indistinguishable from a real human".

## In Scope

- LLM answer generation
- emotion / intent / confidence extraction
- Behavior JSON contract
- Speech Timeline contract
- server-side schema validation
- CC4 `child_test_2 / unreal_file` character mapping
- morph target based facial presets
- V_ viseme or lip-sync mapping
- gaze/head/blink runtime layer
- short gesture keys such as `small_ack`, `explain_small`, `hesitate`, `point_soft`
- CharacterProfile for per-character intensity and style

## Out of Scope

- real-time full-body text-to-motion generation
- DeepMotion runtime calls during live conversation
- MDM/MotionGPT runtime inference
- prompt-to-FBX generation while the user waits
- locomotion-heavy action generation
- several simultaneous characters
- mobile high-quality 3D rendering
- production-scale long-term memory
- human-level naturalness claims

## Recommended Behavior JSON

The LLM should not output low-level morph or bone values.

Recommended:

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
    "ttsStyle": "warm"
  }
}
```

Avoid:

```json
{
  "Mouth_Smile_L": 0.62,
  "Mouth_Smile_R": 0.58,
  "Brow_Raise_Inner_L": 0.21,
  "Jaw_Open": 0.43
}
```

Low-level morph values should live in Unreal DataAssets/DataTables. The LLM chooses behavior intent; Unreal executes the face and body.

## Runtime Layering

```text
Behavior JSON
-> Behavior Planner
-> Unreal Runtime Controller
   -> Face Preset Layer
   -> LipSync / Viseme Layer
   -> Gaze Layer
   -> Blink / Idle Layer
   -> Head Motion Layer
   -> Gesture Montage / Control Rig Layer
```

Layer rule:

- emotion presets control eyes, brows, cheeks, mouth corners
- lip-sync controls jaw, mouth open/close, visemes
- gaze/head/idle run even while waiting for LLM output
- gesture keys select stable montage or Control Rig actions

## MVP Phases

| Phase | Scope | Verification |
|---|---|---|
| 1 | Behavior JSON contract | Korean prompt returns answer + valid behavior schema |
| 2 | CC4 facial runtime | five or more presets blend smoothly on `child_test_2` |
| 3 | TTS/lip-sync/pause | generated speech plays with synced mouth movement |
| 4 | gaze/head/gesture layer | segment behavior triggers gaze, nod, blink, and short gesture |
| 5 | CharacterProfile | same behavior renders differently per character style |
| Later | text-to-motion authoring | generated assets can be imported, validated, and added to gesture library |

## Success Criteria

- The character reacts immediately with listening/thinking idle before the full answer is ready.
- The first spoken response can start from a streamed sentence or short answer segment.
- The face does not jump between random morph values.
- Lip-sync and emotional expression do not fight over the same mouth controls.
- The system can run a repeatable kiosk/exhibition demo with one character and a limited knowledge domain.

