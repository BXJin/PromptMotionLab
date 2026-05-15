# TECH-STACK-DECISION - PromptMotionLab

Updated: 2026-05-13

---

## 0. Decision Summary

PromptMotionLab은 **Python FastAPI AI Server + Unreal Runtime Client** 구조로 간다.

현재 핵심은 editor-only motion authoring tool이 아니라, Unreal 캐릭터가 LLM 답변을 실시간으로 표현하는 runtime AI character agent다.

```text
User Prompt
-> AI Server
-> LLM Answer + Behavior JSON
-> TTS / Lip Sync Timing
-> Unreal Character Runtime
-> expression + gaze + head + voice + short gesture
```

기존 PromptMotionEditor 플러그인은 개발/검증용 도구로 유지할 수 있지만, 최종 제품의 중심은 runtime controller다.

---

## 1. Recommended Stack

| Area | Choice | Reason |
|---|---|---|
| AI Server | Python FastAPI | LLM, TTS, schema validation, memory, provider 전환에 적합 |
| Contract | Pydantic + JSON Schema | Behavior JSON을 엄격하게 검증 |
| LLM | Provider interface | OpenAI/Claude/Gemini/API LLM과 Local LLM을 교체 가능하게 유지 |
| Local LLM | Later: Gemma/Qwen/Llama + PyTorch worker | 보안/오프라인 환경용. 기본 MVP dependency에는 넣지 않음 |
| TTS | Provider interface | ElevenLabs/Azure/로컬 TTS 교체 가능 |
| MVP TTS | Azure Speech TTS | Python SDK와 viseme event를 통해 음성/입모양 timing을 함께 검증 가능 |
| High Quality TTS | ElevenLabs | 음성 자연스러움과 캐릭터성 비교 후보 |
| Lip Sync | Azure viseme first; later OVR LipSync or Audio2Face | CC4의 V_ viseme morph와 연결 가능성 검증 |
| Unreal Runtime | C++ Actor Component + AnimInstance/Blueprint layer | packaged app에서 캐릭터 반응을 안정적으로 실행 |
| Facial Control | SkeletalMeshComponent.SetMorphTarget | CC4 child 캐릭터의 265개 morph target 활용 |
| Eye/Head | Bone control / Control Rig / AnimBP | eye/head 반응은 별도 layer로 유지 |
| Short Gesture | Control Rig 또는 gesture animation library | 큰 motion generation 대신 짧은 대화 반응 중심 |
| Character Config | DataAsset + JSON profile | 캐릭터별 표현 강도, 목소리, 시선 스타일 분리 |
| Storage | SQLite 또는 local JSON for MVP | 대화 로그, prompt, behavior trace 저장 |

---

## 2. Current Character Decision

1차 MVP는 MetaHuman이 아니라 현재 프로젝트의 CC4 계열 `child_test_2 / unreal_file` 캐릭터로 진행한다.

이유:

```text
- 현재 프로젝트에 이미 들어와 있음
- MetaHuman보다 가볍다
- 265개 morph target과 V_ viseme 계열을 확인했다
- eye/jaw/head 계열 bone이 있다
- MVP 수준의 표정/시선/립싱크/고개 반응 검증이 가능하다
```

제약:

```text
- MetaHuman 수준의 facial bone precision은 기대하지 않는다
- ARKit 52 표준 이름을 그대로 쓴다고 가정하지 않는다
- morph target mapping table을 먼저 만들어야 한다
- body gesture는 skeleton mismatch 때문에 별도 retargeting 또는 test BP 검증이 필요하다
```

---

## 3. Core Contracts

### Behavior JSON

LLM 답변과 캐릭터 행동을 묶는 runtime contract다.

```text
answerText
emotion
intent
confidence
segments[]
  - text
  - start
  - duration
  - expression preset/intensity
  - gaze target/stability
  - head nod/tilt
  - gesture preset/intensity
  - pause/filler
```

### CharacterProfile

같은 Behavior JSON이라도 캐릭터마다 다르게 표현하기 위한 profile이다.

```text
voice provider/id
expression intensity scale
blink rate
gaze directness
gesture scale/frequency
speech filler style
pause scale
```

### CharacterCapability

캐릭터별로 가능한 제어 범위를 명시한다.

```json
{
  "characterId": "child_test_2",
  "supportsMorphTargets": true,
  "supportsVisemes": true,
  "supportsEyeBones": true,
  "supportsFacialBones": false,
  "supportsBodyControlRig": "partial",
  "notes": "CC4 morph based face; UE4 skeleton body path requires retargeting"
}
```

---

## 4. Python / PyTorch Decision

Python은 MVP에 사용한다.

```text
사용:
- FastAPI server
- LLM provider
- Behavior Planner
- TTS provider
- schema validation
- conversation memory
- behavior trace 저장
```

PyTorch는 지금 당장 사용하지 않는다.

```text
나중에 사용:
- Gemma/Qwen/Llama 같은 local LLM
- local TTS
- optional local motion generation experiment
```

기본 서버는 `torch` 없이 실행되어야 한다. 로컬 LLM은 별도 worker와 별도 requirements로 분리한다.

```text
Server-Python/
  app/
    providers/
      llm/
        api_llm_provider.py
        local_llm_provider.py
    services/
      behavior_planner.py
      tts_service.py
  workers/
    local_llm/
      requirements-local-llm.txt
```

---

## 5. Unreal Architecture Direction

최종 runtime 구조:

```text
APromptMotionCharacterActor
  - SkeletalMeshComponent
  - PromptMotionRuntimeComponent
  - AudioComponent

UPromptMotionRuntimeComponent
  - receives Behavior JSON
  - schedules segment timeline
  - applies expression/gaze/head/gesture layers

UCharacterExpressionAdapter
  - maps expression preset -> morph target weights

UCharacterLipSyncAdapter
  - maps viseme timing -> V_ morph targets / jaw

UCharacterGazeAdapter
  - maps gaze target -> eye/head control

UCharacterGestureAdapter
  - maps gesture preset -> Control Rig or animation montage
```

Editor plugin은 아래 용도로 남긴다.

```text
- Behavior JSON 테스트
- morph mapping 디버그
- selected actor preview
- generated prompt/export 확인
- 나중에 motion authoring pipeline 실험
```

---

## 5.1 Speech Timeline Direction

TTS는 audio만 반환하지 않는다. 서버는 음성, viseme, 표정, 시선, 고개, pause를 같은 시간축에 올린 `Speech Timeline`을 반환한다.

```text
Behavior Planner:
- answer segment
- expression
- gaze
- head
- pause/filler

TTS Provider:
- audio file/stream
- voice settings
- SSML

Lip Sync Provider:
- viseme id
- audio offset

Unreal Runtime:
- audio playback
- SetMorphTarget for viseme
- expression morph blending
- gaze/head layer
- short gesture layer
```

MVP는 Azure Speech TTS + Azure viseme event를 먼저 사용한다. ElevenLabs는 자연스러운 음성 비교 후보이고, Audio2Face는 더 높은 facial animation 품질이 필요할 때 검토한다.

---

## 6. DeepMotion / MDM Position

DeepMotion, MDM, MotionGPT는 MVP runtime 핵심 경로가 아니다.

정확한 위치:

```text
Runtime path:
LLM -> Behavior JSON -> preset/morph/curve/control rig execution

Authoring path later:
Prompt -> DeepMotion/MDM/MotionGPT -> FBX/BVH/AnimSequence -> gesture library 등록
```

DeepMotion API가 별로이거나 접근이 제한되면 수동 웹 입력도 고려한다.

```text
1. 우리 시스템이 original prompt와 enriched prompt를 저장
2. 사용자가 DeepMotion 웹에 직접 입력
3. 결과 FBX/BVH/GLB를 다운로드
4. ManualMotionProvider로 등록
5. Unreal에서 import/retarget/preview
```

이 구조는 후순위다. 현재 MVP를 막는 요소가 아니다.

---

## 7. Implementation Order

```text
1. Behavior JSON schema 정리
2. child_test_2 morph/viseme mapping table 작성
3. Unreal RuntimeComponent에서 SetMorphTarget preview
4. eye/head/gaze layer 추가
5. TTS audio playback과 lip sync timing 연결
6. CharacterProfile 적용
7. 짧은 gesture preset 연결
8. DeepMotion/MDM authoring pipeline은 이후 분리 진행
```

---

## 8. Success Criteria

MVP 성공 기준:

```text
- 질문에 대한 답변이 텍스트와 음성으로 나온다
- 답변 감정에 맞는 표정이 실시간으로 바뀐다
- 말하는 동안 눈 깜빡임, 시선 이동, 고개 움직임이 자연스럽다
- pause에서 캐릭터가 멈춘 인형처럼 보이지 않는다
- CC4 child 캐릭터 기준으로 친구와 대화하는 듯한 최소 존재감이 나온다
```
