# PROJECT-OVERVIEW - PromptMotionLab

Updated: 2026-05-13

---

## 0. 한 줄 정의

PromptMotionLab은 Unreal 기반 3D 캐릭터가 LLM 답변의 감정과 의도를 실시간으로 표현하게 만드는 **Runtime AI Character Agent** 프로젝트다.

핵심은 AI가 텍스트나 음성만 출력하는 것이 아니라, 답변과 동시에 표정, 시선, 고개 움직임, 짧은 제스처, 말 사이의 pause, 추임새를 함께 실행해 실제 친구와 대화하는 듯한 존재감을 만드는 것이다.

---

## 1. 현재 우선순위

현재 MVP 우선순위는 motion generation이 아니다.

```text
1. 사용자 입력
2. LLM 답변 생성
3. 답변의 감정/의도 분석
4. Behavior JSON / Behavior Timeline 생성
5. Unreal 캐릭터가 표정, 시선, 고개, 립싱크, 짧은 제스처를 실시간 실행
```

DeepMotion, MDM, MotionGPT 같은 text-to-motion 계열은 버리는 것이 아니라 후순위로 둔다. 이들은 실시간 대화 반응 생성기가 아니라, 새 gesture asset을 제작하고 검증하는 authoring pipeline으로 사용한다.

---

## 2. MVP 대상 캐릭터

1차 MVP는 현재 프로젝트의 `child_test_2 / unreal_file` 캐릭터를 기준으로 검증한다.

확인된 구조:

```text
SkeletalMesh: /Game/child_test_2/mesh/unreal_file
Skeleton: /Game/Characters/Mannequin_UE4/Meshes/SK_Mannequin_Skeleton
Morph Target: 265개
Facial Curve: 319개
Facial Bone: jaw, eye, tongue, teeth, head, neck 계열
```

판단:

```text
가능:
- 눈 깜빡임
- 시선 이동
- 고개 끄덕임/기울임
- 미소, 고민, 놀람 등 morph 기반 표정
- V_ 계열 viseme morph 기반 립싱크
- 짧은 상체/손 제스처

주의:
- MetaHuman 수준의 세밀한 facial bone 제어는 목표로 잡지 않는다.
- ARKit 52 표준 이름이 그대로 있다고 가정하지 않는다.
- 실제 morph 이름 매핑 테이블을 만들어 검증해야 한다.
```

따라서 현재 캐릭터로도 MVP 수준의 "실시간 느낌"은 검증 가능하다. 단, 표현 정밀도는 MetaHuman보다 낮을 수 있으므로 CC4 morph/viseme 기반 캐릭터라는 전제를 문서와 코드에 명확히 둔다.

---

## 3. 핵심 사용자 경험

```text
사용자가 캐릭터에게 질문하거나 말을 건다.
-> LLM이 답변을 생성한다.
-> Behavior Planner가 답변의 감정, 확신도, 의도, 말투를 분석한다.
-> 캐릭터가 말하기 전에 짧게 생각하는 표정과 시선 이동을 한다.
-> TTS 음성과 함께 립싱크가 재생된다.
-> 문장 단위로 표정, 눈썹, 고개, 손 제스처가 자연스럽게 전환된다.
-> 말 사이에 "음...", "아", "그렇죠" 같은 추임새와 pause가 들어간다.
```

좋은 결과의 기준은 큰 전신 동작이 아니다. 작은 반응이 답변의 의미와 맞아떨어져 캐릭터가 살아있는 것처럼 느껴지는지다.

---

## 4. 시스템 역할

### AI Server

```text
Python FastAPI
- LLM Provider
- Conversation Memory
- Behavior Planner
- TTS Provider
- Lip Sync / Viseme timing adapter
- CharacterProfile 관리
- Behavior JSON schema validation
```

### Unreal Client

```text
Unreal Engine
- 3D character rendering
- Behavior JSON 수신
- Morph target 제어
- Eye / head / gaze 제어
- Control Rig / Animation Blueprint 기반 짧은 gesture
- TTS audio playback
- Lip sync curve 적용
- idle layer: blink, breathing, micro gaze, head settle
```

---

## 5. 프로젝트가 아닌 것

현재 MVP는 아래를 목표로 하지 않는다.

```text
- runtime full-body text-to-motion generation
- DeepMotion API 자동화 의존
- 모든 skeleton 자동 대응
- MetaHuman급 facial bone precision 보장
- 범용 animation marketplace
- 복잡한 locomotion, dance, object interaction 생성
```

이 기능들은 후순위 확장으로 분리한다.

---

## 6. 장기 확장 방향

```text
MVP:
CC4 child 캐릭터 기반 실시간 표정/시선/고개/립싱크/짧은 gesture

다음:
CharacterProfile로 캐릭터별 말투, 목소리, 표정 강도, 시선 안정성, 추임새 스타일 분리

후순위:
MetaHuman adapter
DeepMotion / MDM / MotionGPT 기반 gesture asset authoring
모바일/키오스크 최적화
운영 웹 대시보드
로컬 LLM / 로컬 TTS
```

---

## 7. 포트폴리오 소개 문장

```text
PromptMotionLab은 LLM 답변을 Behavior JSON으로 구조화하고,
Unreal 3D 캐릭터가 표정, 시선, 고개 움직임, 립싱크, 짧은 제스처로 실시간 표현하게 만드는 AI Character Agent 시스템입니다.

현재 MVP는 MetaHuman이 아닌 CC4 기반 child 캐릭터로 검증하며,
265개 morph target과 V_ viseme morph를 활용해 친구와 대화하는 듯한 미세 반응을 우선 구현합니다.
DeepMotion, MDM, MotionGPT는 실시간 대화의 핵심 경로가 아니라 후속 gesture asset 제작 파이프라인으로 분리합니다.
```
