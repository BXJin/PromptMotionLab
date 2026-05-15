# Behavior JSON Multi-Renderer Strategy

Updated: 2026-05-15

## Summary

The first MVP renderer is **Unreal Engine**.

However, Behavior JSON should not be designed as an Unreal-only format. The long-term value is the middle layer that converts an AI response into character behavior policy:

```text
LLM / RAG
-> Behavior JSON
-> Behavior Planner
-> Renderer Adapter
   -> Unreal
   -> MetaHuman
   -> Unity / BlendShape Avatar
   -> Video Avatar API
   -> Web / Three.js / VRM Avatar
   -> Live2D
```

This means PromptMotionLab's core asset is not only "an Unreal character". The core asset is a renderer-agnostic behavior contract that can drive different avatar systems.

## MVP Decision

Do not change the MVP direction.

Build the first working version in Unreal:

```text
Behavior JSON
-> Unreal Runtime Character Controller
-> facial preset + gaze + blink + head motion + lip sync + short gesture
```

Unreal remains the first implementation because it can prove the hardest part of the target use case: spatial character presence, object-aware gaze, gesture, and kiosk/exhibition rendering.

## Why Keep Unreal First?

Most real-time avatar products are video-avatar or browser-avatar oriented. They are strong for fast deployment and realistic talking faces.

Unreal is harder and heavier, but it is better for:

- exhibition and showroom spaces
- kiosk and fixed-display installations
- 3D object-aware gaze and pointing
- brand/IP character rendering
- spatial camera, lighting, UI, and interaction design
- Control Rig / AnimBP based gesture execution
- future digital twin or game-like environments

The product should not claim "Unreal is always better". The correct claim is:

```text
Video avatars are strong for realistic face-to-face video conversation.
Unreal is strong for spatial, controllable, object-aware character experiences.
```

## Core Behavior JSON

The core schema should stay compact and renderer-independent.

```json
{
  "reply": "제가 가진 자료 기준으로는 이 전시물의 핵심은 움직임을 통해 감정을 전달한다는 점이에요.",
  "behavior": {
    "emotion": "friendly",
    "intensity": 0.6,
    "confidence": 0.84,
    "intent": "explain",
    "gaze": "user",
    "gestureKey": "explain_small",
    "headMotion": "small_nod",
    "speechStyle": "warm",
    "safetyState": "normal"
  }
}
```

The LLM should not output renderer-specific values in the common contract:

- no Unreal morph target names
- no MetaHuman curve names
- no Unity BlendShape names
- no ARKit blendshape values
- no video API-specific emotion parameter names
- no frame-by-frame animation data

Renderer-specific values belong in adapter mappings.

## Renderer Adapter Pattern

```text
Behavior JSON
-> Behavior Planner
-> CharacterProfile
-> RendererCapability
-> RendererAdapter
```

Each adapter maps the same behavior to its own rendering system.

### Unreal Adapter

```text
emotion=friendly, intensity=0.6
-> FacePreset_FriendlyExplain at 60%

gaze=user
-> eye/head look-at target

gestureKey=explain_small
-> AnimMontage_ExplainSmall or ControlRig action

speechStyle=warm
-> TTS style preset
```

### MetaHuman Adapter

```text
emotion=friendly
-> MetaHuman facial control rig preset / ARKit curve profile

gaze=user
-> MetaHuman eye/head control

gestureKey=explain_small
-> compatible montage or Control Rig sequence
```

### Unity / BlendShape Adapter

Unity can render the same behavior contract with `SkinnedMeshRenderer` BlendShape weights.

```text
emotion=friendly, intensity=0.6
-> MouthSmile, CheekRaise, EyeSquint blendshape group at 60%

gaze=user
-> eye/head look-at target

gestureKey=explain_small
-> Animator clip or Timeline clip
```

Unreal Morph Target and Unity BlendShape are equivalent at the behavior-contract level:

```text
Unreal Morph Target ~= Unity BlendShape
```

Renderer-specific names such as `MouthSmile`, `EyeBlink`, `BrowRaise`, or `JawOpen` should stay inside the Unity adapter mapping, not in the common Behavior JSON.

ARKit-style 52 blendshapes can be used as an intermediate mapping profile when the avatar or face tracking provider supports them.

### Video Avatar Adapter

Video avatar APIs may not expose fine-grained expression control. The adapter should degrade gracefully.

```text
emotion=friendly
-> provider expression="smile" if supported
-> otherwise voiceStyle="warm" and prompt-level style instruction

gaze=user
-> ignored if unsupported

gestureKey=explain_small
-> ignored or mapped to "subtle head motion" if supported
```

### Web / VRM Adapter

```text
emotion=friendly
-> VRM expression preset, GLB morph target group, or ARKit blendshape group

gaze=user
-> VRM lookAt target

gestureKey=explain_small
-> animation clip
```

Web renderers such as Three.js, Babylon.js, or React Three Fiber can drive GLB/VRM avatars by changing morph target values in real time.

```text
Behavior JSON
-> Web Renderer Adapter
-> GLB / VRM avatar
-> morphTargetInfluences / expression manager
-> real-time face expression
```

This makes web avatars suitable for a later lightweight demo or browser-based product surface. They should still consume the same renderer-independent behavior contract.

### Live2D Adapter

```text
emotion=friendly
-> Live2D expression file

gaze=down_left
-> eye parameter / head parameter

gestureKey=explain_small
-> Live2D motion file
```

## Renderer Capability

Each renderer should declare what it can actually do.

```json
{
  "renderer": "video_avatar",
  "supportsExpressionPreset": true,
  "supportsExpressionIntensity": false,
  "supportsGaze": false,
  "supportsHeadMotion": true,
  "supportsGesture": false,
  "supportsLipSync": true,
  "supportsSpeechStyle": true,
  "supportsBlendShapeMapping": false,
  "supportsArkit52Mapping": false
}
```

The Behavior Planner can then choose what to preserve and what to drop.

Example:

```text
If supportsGesture=false:
  gestureKey is not executed.
  Optional: increase headMotion or speechStyle to compensate.

If supportsGaze=false:
  gaze target is ignored.

If supportsExpressionIntensity=false:
  map intensity ranges to discrete presets.
```

## CharacterProfile

CharacterProfile is renderer-independent where possible.

```json
{
  "characterId": "calm_guide",
  "style": {
    "expressiveness": 0.55,
    "gestureScale": 0.6,
    "gazeStability": 1.2,
    "speechWarmth": 0.7,
    "pauseScale": 1.0
  }
}
```

Renderer adapters can translate these values to native settings.

## Safety and Honesty

The system should not claim that AI feels emotions.

Correct framing:

```text
The system estimates the answer's intent, emotional tone, confidence, and conversational state, then expresses that state through avatar behavior.
```

Avoid:

```text
AI feels emotion.
AI has real emotions.
```

## Strategic Position

Competitors often combine:

```text
LLM + TTS + Avatar Renderer
```

PromptMotionLab should emphasize:

```text
LLM + Behavior Policy Layer + Multi-Renderer Character Runtime
```

The first renderer is Unreal. Later renderers can include video avatars, browser avatars, VRM, Live2D, and MetaHuman.

## Practical Roadmap

1. Implement Unreal adapter first.
2. Keep Behavior JSON renderer-independent.
3. Add CharacterProfile and RendererCapability.
4. Add one simple secondary adapter later, such as Web/VRM, Unity, or Live2D.
5. Only after runtime behavior is stable, test video avatar API mapping.
