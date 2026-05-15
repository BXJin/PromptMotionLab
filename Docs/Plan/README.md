# PromptMotionLab Plan Index

Updated: 2026-05-14

This directory is split by product priority.

## Priority 1 - Runtime AI Character Control

Current MVP work is in `10-RuntimeCharacter`.

Goal:

```text
User voice/text
-> LLM/RAG response
-> Behavior JSON / Speech Timeline
-> Unreal runtime character controller
-> facial preset + gaze + blink + head motion + lip sync + short gesture
```

The MVP does not generate full-body motion at runtime. The runtime path uses predefined facial presets, gesture keys, animation montages, Control Rig/AnimBP layers, and lip-sync timing so the character can react with low perceived latency.

Competitor research does not change the first MVP: start with Unreal. The longer-term architecture should keep Behavior JSON renderer-agnostic so it can later drive video avatars, web/VRM avatars, Live2D, or MetaHuman adapters.

Start here:

- `00-Current/CURRENT-DIRECTION.md`
- `00-Current/MVP-PLAN.md`
- `00-Current/COMPETITOR-ANALYSIS.md`
- `00-Current/MARKET-AND-CAREER-STRATEGY.md`
- `10-RuntimeCharacter/RUNTIME-AI-CHARACTER-AGENT-PLAN.md`
- `10-RuntimeCharacter/BEHAVIOR-JSON-MULTI-RENDERER-STRATEGY.md`
- `10-RuntimeCharacter/TTS-LIPSYNC-TIMELINE-PLAN.md`

## Later - Motion Authoring / Text-to-Motion

Future motion generation work is in `20-MotionAuthoring`.

Goal:

```text
Prompt
-> text-to-motion / provider / offline generation
-> FBX/BVH/AnimSequence
-> import / retarget / validate / bake
-> runtime gesture library
```

Text-to-motion is not the first MVP path. It is a later authoring pipeline for creating or enriching gesture assets that the runtime character can select and blend.

## Directory Map

| Directory | Purpose |
|---|---|
| `00-Current` | Current product direction, MVP scope, stack decisions, high-level architecture |
| `10-RuntimeCharacter` | Priority 1 runtime character control: Behavior JSON, TTS/lip-sync, facial presets, gaze, Control Rig gestures |
| `20-MotionAuthoring` | Later text-to-motion, provider research, motion import/retarget/validation/bake pipeline |
| `90-Notes` | Raw notes, application drafts, checklists |
