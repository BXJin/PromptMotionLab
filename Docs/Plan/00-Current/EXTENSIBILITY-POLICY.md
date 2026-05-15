# EXTENSIBILITY-POLICY - PromptMotionLab

Updated: 2026-05-12

---

## 0. Rule

Build the MVP around UE5 Manny, but do not design the system as if Manny is the only possible character.

The project must support future expansion in these directions:

```text
- different UE skeletons
- SkeletalMesh assets with facial bones
- finger controls
- custom Control Rigs
- local LLM providers such as Gemma/Qwen/Llama
- commercial T2M providers such as DeepMotion
- manual web-generated motion files
```

---

## 1. MVP Character Policy

```text
Primary target:
- UE5 Manny / Quinn compatible skeleton
- Manny Control Rig
- upper-body gesture preview first
```

Phase 1 required controls:

```text
root
pelvis
spine
neck/head
clavicle_l/r
upperarm_l/r
lowerarm_l/r
hand_l/r
```

Phase 1 optional or ignored controls:

```text
finger bones
facial bones
eye controls
mouth controls
cloth/hair/secondary controls
```

---

## 2. Facial Bone Policy

Some SkeletalMesh assets may include facial bones. Do not animate them in Phase 1.

Emotion should remain semantic:

```text
emotion: happy
style: friendly
```

Phase 1 usage:

```text
- enriched prompt wording: "happy", "friendly", "smiling"
- gesture style: softer posture, head tilt, energetic wave
- no direct facial bone animation
```

Later usage:

```text
- FacePoseAdapter
- facial expression curves
- eye look controls
- mouth shape controls
```

---

## 3. Adapter Boundaries

Do not hard-code character-specific behavior into `MotionSpec`.

Use this flow:

```text
MotionSpec
-> ProceduralGestureMapper
-> SkeletonPreset
-> ControlRigAdapter
-> Preview/Bake
```

Recommended Unreal folders:

```text
ControlRig/
  Presets/
    MannySkeletonPreset
  Adapters/
    MannyControlRigAdapter
    FacePoseAdapter later
    FingerPoseAdapter later
```

Recommended server contracts:

```text
MotionSpec
SkeletonPreset
SkeletonCapabilities
ProceduralGestureJson
```

---

## 4. Skeleton Capability Example

```json
{
  "skeletonPreset": "ue5_manny",
  "capabilities": {
    "upperBodyIk": true,
    "fingerControls": false,
    "facialControls": false,
    "headLook": true,
    "rootMotion": false
  }
}
```

The backend can generate the same `MotionSpec`, while the Unreal adapter decides how much of it can be applied to the selected character.

---

## 5. LLM Provider Expansion

MVP:

```text
ApiLlmProvider
-> hosted LLM API
-> MotionSpec / ProceduralGestureJson / EnrichedPrompt
```

Later:

```text
LocalLLMProvider
-> Gemma/Qwen/Llama
-> transformers + PyTorch in separate worker
```

The default server must not require PyTorch. Local inference should be optional and isolated.

---

## 6. Commercial T2M Expansion

Commercial motion comparison is later than procedural preview.

The extension path is:

```text
Prompt snapshots
-> manual DeepMotion web generation
-> ManualMotionProvider registration
-> UE Import/Retarget/Preview
-> later DeepMotionProvider API automation
```

Do not block the MVP on commercial API quality or availability.
