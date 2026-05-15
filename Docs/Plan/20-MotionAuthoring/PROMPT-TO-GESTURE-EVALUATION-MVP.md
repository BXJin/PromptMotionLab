# Prompt-to-Gesture Evaluation MVP

작성일: 2026-05-05

## 0. 목적

이 문서는 현재 전시 프로젝트 이후 별도 포트폴리오로 검토하는 Unreal 기반 AI animation tool 기획이다.

목표는 "상용 text-to-motion API를 붙였다"를 보여주는 것이 아니라, 같은 사용자 prompt를 두 가지 방식으로 처리하고 품질, 비용, 안정성, Unreal 적용성을 비교하는 것이다.

```text
Pipeline A: LLM -> procedural JSON -> Control Rig preview
Pipeline B: prompt/constraint -> commercial text-to-motion -> import/retarget/preview/bake
```

핵심 질문:

```text
간단한 gesture는 procedural JSON으로 충분한가?
상용 text-to-motion은 비용과 라이선스 리스크를 감수할 만큼 품질이 좋은가?
두 방식을 Unreal Editor workflow 안에서 비교하고 선택할 수 있는가?
```

## 1. 프로젝트 포지션

프로젝트 이름 후보:

```text
Prompt-to-Gesture Evaluation Tool for Unreal
AI Motion Pipeline Evaluator
Unreal AI Gesture Preview & Bake Tool
```

정확한 포지션:

```text
Unreal Editor 안에서 자연어 prompt를 입력하고,
LLM 기반 procedural gesture와 상용 text-to-motion 결과를 같은 캐릭터에서 비교한 뒤,
실무적으로 쓸 수 있는 결과만 AnimSequence로 bake하는 툴.
```

피해야 할 포지션:

```text
완벽한 AI animation generator
로컬 MDM/MotionGPT 완전 통합 제품
모든 skeleton에 자동 대응하는 범용 retargeter
runtime full-body text-to-motion system
```

## 2. MVP A: LLM 기반 Procedural JSON Preview

### 2.1 개념

사용자 prompt를 LLM이 high-level gesture JSON으로 변환하고, Unreal Control Rig가 이 값을 실제 캐릭터 움직임으로 바꾼다.

```text
Prompt
-> LLM
-> high-level procedural JSON
-> Unreal Control Rig
-> preview
```

예:

```text
사용자: "웃으면서 오른손으로 인사하듯 손 흔들어줘"
```

LLM 출력:

```json
{
  "gesture": "wave",
  "hand": "right",
  "bodyPart": "upper_body",
  "emotion": "happy",
  "duration": 1.8,
  "amplitude": 0.65,
  "speed": 1.2,
  "shoulderRaise": 0.25,
  "elbowBend": 0.45,
  "bodyLean": 0.08,
  "rootMotion": false,
  "feetPlanted": true
}
```

중요한 점:

```text
LLM이 upperarm_r 같은 bone transform을 직접 만들지 않는다.
LLM은 gesture parameter를 만들고, Control Rig가 실제 bone transform을 계산한다.
```

### 2.2 UE 필요 구성

최소 구성:

```text
UE Manny 또는 고정 humanoid character 1종
Control Rig asset
Editor Utility Widget 또는 Editor Plugin UI
JSON gesture schema
Prompt -> JSON LLM 호출
Preview actor
```

Control Rig에 필요한 control:

```text
right_hand_ik
left_hand_ik
head_look
spine_bend
chest_twist
elbow_pole_vector
```

처음 지원할 gesture:

```text
wave
point
bow
nod
explain
```

제외:

```text
walk
run
jump
dance
sit/stand
object interaction
```

### 2.3 장점과 한계

장점:

```text
API generation 비용이 거의 없음
즉시 preview 가능
실패해도 비용 손실이 작음
runtime/editor 둘 다 확장 가능
파라미터 조정이 쉬움
단순 NPC gesture에는 실무적으로 쓸 수 있음
```

한계:

```text
진짜 text-to-motion generation은 아님
Control Rig 품질에 크게 의존
복잡한 full-body motion은 부자연스러움
gesture 종류를 직접 설계해야 함
```

## 3. MVP B: Enriched Prompt T2M Pipeline

### 3.1 개념

Pipeline A에서 생성된 Procedural JSON을 enriched prompt로 변환해 상용 T2M API에 전달한다.
단순 원본 프롬프트로 호출한 결과(B-plain)와 비교해,
구조화된 파라미터가 T2M 결과 품질을 실제로 개선하는지 검증한다.

```text
[B-enriched 흐름]
원본 Prompt
-> Pipeline A (LLM → Procedural JSON)
-> Procedural JSON → enriched prompt 변환
-> commercial T2M API
-> generated FBX/BVH/GLB
-> Unreal import → retarget → preview → approve → AnimSequence bake

[B-plain 흐름 — 비교 기준]
원본 Prompt
-> (정규화 없이 또는 단순 번역만)
-> commercial T2M API
-> generated FBX/BVH/GLB
-> Unreal import → retarget → preview
```

초기에는 공식 API 계약 없이 manual provider로 시작한다.

```text
상용 웹에서 plain / enriched prompt 각각으로 수동 생성
-> FBX/BVH/GLB 다운로드
-> 서버 ManualMotionProvider 폴더에 업로드
-> UE Plugin이 API 결과처럼 처리
```

이 방식은 비용과 라이선스 리스크를 줄이면서도 전체 workflow와 비교 실험을 검증할 수 있다.

### 3.2 Provider 후보

상용/서비스:

```text
DeepMotion SayMotion
Rokoko Text-to-Motion
Kimodo
nocapmocap
Rigtix
```

오픈소스/자가 호스팅 후보:

```text
MDM
MotionGPT
MotionDiffuse
T2M-GPT
MotionLCM
HY-Motion 계열
```

현실 판단:

```text
초기 MVP: 상용/수동 생성 결과를 manual provider로 연결
중기: API 제공 provider 1개 연동
장기: RunPod/Colab 기반 오픈소스 model provider 실험
```

### 3.3 비용 설계

나쁜 구조:

```text
Preview 요청 -> API generation 1회 과금
Bake 요청 -> API generation 재호출 1회 과금
```

좋은 구조:

```text
Generate once
-> generated result cache
-> preview many times
-> bake once
```

즉, 비용은 generation에만 발생해야 한다.

```text
generation 비용 = 상용 API 또는 GPU inference 비용
preview 비용 = 0원에 가까움
bake 비용 = 로컬 처리 비용
```

캐시 정책:

```text
사용자별 private cache만 허용
다른 사용자에게 generated motion file 공유 금지
공용 저장은 prompt, tag, quality metadata 중심
```

## 4. 비교 실험

### 4.1 첫 실험 주제

처음 비교 대상은 하나로 제한한다.

```text
Gesture: friendly right-hand wave
Character: UE Manny
Duration: 1.5~2.0 sec
Root motion: false
Feet: planted
Emotion: happy
```

Prompt:

```text
웃으면서 오른손으로 인사하듯 손 흔들어줘.
```

세 결과물:

```text
[A]          LLM -> procedural JSON -> Control Rig wave

[B-plain]    원본 프롬프트 그대로 (또는 단순 번역)
             -> T2M API -> Generated FBX

[B-enriched] LLM -> procedural JSON
             -> JSON 파라미터 기반 enriched prompt 생성
             -> T2M API -> Generated FBX
```

### 4.2 Enriched Prompt 예시

```text
Procedural JSON:
{
  "gesture": "wave", "hand": "right", "emotion": "happy",
  "duration": 1.8, "speed": 1.2, "amplitude": 0.65,
  "shoulderRaise": 0.25, "elbowBend": 0.45,
  "feetPlanted": true, "rootMotion": false
}

B-plain prompt:
"A character smiles and waves hello with the right hand."

B-enriched prompt:
"A happy character waves hello with the right hand.
 Upper body only. Arm raised (shoulder lift: moderate),
 elbow moderately bent. Wrist oscillation at medium-high amplitude.
 Slightly fast speed. Duration 1.8 seconds.
 Feet firmly planted on ground. No root motion."
```

### 4.3 비교 기준

```text
항목                | A (Procedural) | B-plain        | B-enriched
생성 비용           | LLM만          | Provider 비용   | Provider 비용
gesture 정확도     | 높음           | 낮음~중간        | 높음 (기대)
자연스러움          | 중간           | 중간~높음        | 높음 (기대)
발 고정 여부        | 완벽           | 검증 필요        | 검증 필요 (명시 덕에 낮을 것)
root drift          | 없음           | 검증 필요        | 검증 필요 (명시 덕에 낮을 것)
반복 안정성         | 높음           | 낮음            | 중간 (constraint로 편차 감소 기대)
파라미터 수정       | 쉬움           | 재생성 필요      | JSON 수정 후 재생성
```

검증하려는 가설:

```text
Procedural JSON 기반 enriched prompt가
단순 프롬프트 대비 T2M API 결과 품질을 개선한다.
특히 gesture 종류, constraint(feet planted, no root motion) 준수,
결과 편차 감소 측면에서 개선 효과가 있을 것으로 예상한다.
```

## 5. 기술 스택

### 5.1 UE Tool

추천:

```text
Unreal Engine 5
C++ Editor Plugin 또는 Editor Utility Widget
Slate / Details Panel UI
Control Rig
IK Rig / IK Retargeter
Animation Sequence bake
HTTP client
JSON parser
```

1차는 Editor Utility Widget으로 빠르게 검증하고, 구조가 잡히면 C++ Editor Plugin으로 옮긴다.

### 5.2 Backend

초기:

```text
FastAPI 또는 ASP.NET Core
ManualMotionProvider
PromptNormalizer
Job API
Local file storage
SQLite metadata
```

이 프로젝트는 motion model/Python 생태계 연결 가능성이 있으므로 FastAPI가 유리하다. 다만 기존 전시 프로젝트에서 ASP.NET Gateway 경험이 있으므로 ASP.NET Core도 가능하다.

Provider interface:

```text
IMotionProvider
- ManualMotionProvider
- CommercialApiProvider
- LocalModelProvider
- ProceduralJsonProvider
```

### 5.3 AI

LLM 역할:

```text
Prompt normalization
High-level procedural JSON generation
Commercial T2M prompt refinement
Constraint generation
Quality report summary
```

LLM이 하지 않는 것:

```text
frame별 full-body bone transform 직접 생성
모든 skeleton에 대한 완전한 retarget 자동 해결
상용 API 결과물 라이선스 판단
```

## 6. 로드맵

### Phase 1: Procedural JSON Preview

```text
UE Manny 고정
Control Rig wave/point/bow 구현
Prompt -> LLM -> JSON
JSON -> Control Rig preview
```

결과물:

```text
비용 거의 없는 LLM-driven gesture preview
```

### Phase 2: Manual Commercial Result Pipeline

```text
상용 툴에서 wave motion 수동 생성
FBX/BVH 다운로드
ManualMotionProvider에 등록
UE에서 import/retarget/preview/bake
```

결과물:

```text
진짜 generated motion result를 Unreal pipeline에 연결
```

### Phase 3: Comparison UI

```text
왼쪽: Procedural JSON result
오른쪽: Commercial T2M result
비교 metric 표시
approve/bake 선택
```

결과물:

```text
비용 대비 품질 판단이 가능한 실험형 툴
```

### Phase 4: Provider 확장

```text
Commercial API Provider
RunPod/Colab generated result Provider
Local MDM/MotionGPT Provider stub
```

결과물:

```text
장기적으로 로컬/클라우드 generation provider 교체 가능성 확보
```

## 7. 실무성 판단

이 프로젝트의 실무 가치는 "AI가 완벽한 모션을 만든다"가 아니다.

실무 가치는 다음에 있다.

```text
1. 생성 비용과 품질을 비교할 수 있음
2. 단순 gesture는 procedural로 빠르게 처리 가능
3. 복잡한 동작은 commercial T2M 후보와 비교 가능
4. generated motion을 Unreal에서 바로 검증 가능
5. 마음에 드는 결과만 AnimSequence로 bake 가능
6. private cache로 비용 중복을 줄임
7. 라이선스 리스크가 큰 공용 asset cache를 피함
```

따라서 포트폴리오 설명은 다음이 적합하다.

```text
자연어 prompt를 LLM 기반 procedural gesture JSON으로 변환해 Unreal Control Rig에서 즉시 preview하고,
동일한 prompt/constraint를 상용 text-to-motion pipeline 결과와 비교한 뒤,
품질과 비용을 기준으로 선택하여 AnimSequence로 bake하는 Unreal Editor 기반 AI animation evaluation tool을 설계했다.
```

## 8. 결론

현재 조건에서 가장 현실적인 다음 프로젝트는 다음이다.

```text
1. LLM-driven procedural JSON gesture preview
2. Commercial/generated motion manual provider
3. 두 결과의 품질/비용/안정성 비교
4. 선택된 결과만 bake
```

이 방향은 순수 text-to-motion 생성 모델 개발보다 작지만, 개인 포트폴리오에서 더 완성도 있게 만들 수 있고 실무 판단력을 보여주기 좋다.
