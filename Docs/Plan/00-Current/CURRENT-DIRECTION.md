# CURRENT-DIRECTION - PromptMotionLab

Updated: 2026-05-14

## Current Decision

PromptMotionLab's first product direction is **Runtime AI Character Control**, not runtime text-to-motion generation.

Competitor research does not change the MVP implementation order. The first renderer remains **Unreal Engine**.

The broader product direction is:

```text
Behavior JSON core first
-> Unreal renderer first
-> later: video avatar / web avatar / MetaHuman / Live2D adapters
```

The MVP should prove that an Unreal character can respond to an AI conversation with low perceived latency:

```text
User Voice/Text
-> LLM / RAG / Memory
-> Behavior JSON + Speech Timeline
-> Unreal Runtime Character Controller
-> facial preset + gaze + blink + head motion + lip sync + short gesture
```

The first target is a kiosk/exhibition-style AI character that feels responsive and expressive. It is not a "human-level digital human" and it does not generate full-body motion on every user prompt.

The system should also avoid claiming that AI feels emotions. The correct framing is that the system estimates an answer's intent, emotional tone, confidence, and conversational state, then expresses those signals through avatar behavior.

## Priority 1 - Runtime Character Path

Build this first:

```text
LLM = decides answer intent, emotion, confidence, gesture key
Behavior Planner = converts those decisions into a character-safe timeline
Unreal = executes facial presets, morph blends, gaze, lip sync, Control Rig, and gesture montages
```

Runtime MVP includes:

- Behavior JSON contract
- Speech Timeline contract
- CC4/child_test_2 morph and viseme mapping
- facial preset blending
- gaze, blink, head nod/tilt
- TTS playback
- viseme or lip-sync layer
- short upper-body gesture keys
- CharacterProfile for style/intensity tuning

Runtime MVP excludes:

- real-time full-body motion generation
- DeepMotion/MDM/MotionGPT runtime inference
- prompt-to-FBX generation during live conversation
- locomotion-heavy actions
- human-level naturalness claims
- production-scale long-term memory and safety guarantees

## Later - Motion Authoring Path

Text-to-motion remains useful, but it is a later authoring pipeline:

```text
Prompt
-> T2M / MDM / MotionGPT / commercial provider
-> generated motion asset
-> import / retarget / validate / bake
-> gesture library
-> runtime selects gesture key
```

The runtime character should select and blend stable gesture assets. It should not depend on live text-to-motion generation to answer a user.

## Document Map

| Path | Role |
|---|---|
| `../README.md` | Plan index and directory split |
| `MVP-PLAN.md` | Runtime-first MVP scope |
| `TECH-STACK-DECISION.md` | FastAPI + Unreal runtime stack |
| `COMPETITOR-ANALYSIS.md` | Competitor landscape and positioning |
| `../10-RuntimeCharacter/RUNTIME-AI-CHARACTER-AGENT-PLAN.md` | Main runtime character plan |
| `../10-RuntimeCharacter/BEHAVIOR-JSON-MULTI-RENDERER-STRATEGY.md` | Behavior JSON as a renderer-agnostic control layer |
| `../10-RuntimeCharacter/TTS-LIPSYNC-TIMELINE-PLAN.md` | TTS, viseme, lip-sync, pause, speech timing |
| `../20-MotionAuthoring/*` | Later text-to-motion and motion provider pipeline |

## Implementation Order

1. Behavior JSON schema
2. child_test_2 morph/viseme mapping
3. Unreal runtime facial preset preview
4. gaze/head/blink layer
5. TTS + lip-sync timing
6. short gesture preset/montage layer
7. CharacterProfile tuning
8. later: text-to-motion authoring and gesture library generation
