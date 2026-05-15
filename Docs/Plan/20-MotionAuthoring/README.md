# Motion Authoring / Text-to-Motion Plans

This directory contains later-stage motion generation and provider research.

These docs are not the first MVP path.

Use this area for:

- DeepMotion / MDM / MotionGPT research
- text-to-motion provider comparison
- prompt-to-motion evaluation
- generated FBX/BVH/AnimSequence import
- retarget / validation / bake
- gesture library generation

Target relationship with runtime:

```text
Authoring:
Prompt -> T2M provider -> motion asset -> validate/bake -> gesture library

Runtime:
Behavior JSON -> gestureKey -> stable gesture asset playback
```

Runtime AI character control remains in `../10-RuntimeCharacter`.

