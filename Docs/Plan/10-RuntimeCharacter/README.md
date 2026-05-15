# Runtime Character Plans

This directory contains the priority 1 plan: low-latency runtime character control.

Use these docs for the current MVP:

- `MVP-DEVELOPMENT-ROADMAP.md`
- `FACE-PRESET-ROADMAP.md`
- `UNREAL-REFERENCE-REUSE-NOTES.md`
- `RUNTIME-AI-CHARACTER-AGENT-PLAN.md`
- `STT-INPUT-REACTION-TIMELINE-PLAN.md`
- `BEHAVIOR-JSON-MULTI-RENDERER-STRATEGY.md`
- `TTS-LIPSYNC-TIMELINE-PLAN.md`
- `PROCEDURAL-JSON-GESTURE-PLAN.md`
- `ProceduralGesture_Roadmap.md`

Boundary:

- Runtime uses Behavior JSON, facial presets, gaze, lip-sync, Control Rig, and gesture montage playback.
- Runtime does not call text-to-motion providers while the user waits.
- Text-to-motion belongs in `../20-MotionAuthoring` as a later gesture asset authoring pipeline.
