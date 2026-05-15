# PROCEDURAL-JSON-GESTURE-PLAN — PromptMotionLab

작성일: 2026-05-05

---

## 0. 개념 요약

LLM이 사용자의 자연어를 **고수준 gesture parameter**로 변환하고, Unreal Control Rig가 해당 parameter를 실제 bone transform으로 계산해 Preview Actor에서 재생한다.

```text
Prompt
→ LLM
→ Procedural Gesture JSON (high-level parameter)
→ Unreal Control Rig
→ Viewport Preview
→ Approve
→ AnimSequence Bake
```

핵심: LLM이 `upperarm_r` 같은 bone quaternion을 직접 만들지 않는다. LLM은 gesture의 **의도와 파라미터**를 만들고, Control Rig이 실제 움직임을 계산한다.

---

## 1. 지원 Gesture 목록

### 1차 MVP 범위

| Gesture | 영어 이름 | 관련 body part |
|---|---|---|
| 손 흔들기 | wave | right/left arm + shoulder |
| 가리키기 | point | right/left arm + index finger |
| 인사 (고개/허리) | bow | spine + head |
| 고개 끄덕이기 | nod | head |
| 설명하기 | explain | both arms + spine |

### 제외 (1차)

```text
walk / run / jump / dance / sit / stand
full-body locomotion
object interaction
facial expression (표정)
finger detail (individual finger control)
```

---

## 2. Procedural Gesture JSON Schema

### 기본 schema

```json
{
  "gesture": "wave",
  "hand": "right",
  "bodyPart": "upper_body",
  "emotion": "happy",
  "duration": 1.8,
  "speed": 1.2,
  "amplitude": 0.65,
  "shoulderRaise": 0.25,
  "elbowBend": 0.45,
  "wristFlip": 0.3,
  "bodyLean": 0.08,
  "headTilt": 0.05,
  "rootMotion": false,
  "feetPlanted": true,
  "loopable": false
}
```

### 필드 정의

| 필드 | 타입 | 범위 | 설명 |
|---|---|---|---|
| gesture | string | wave/point/bow/nod/explain | 동작 종류 |
| hand | string | right/left/both/none | 사용할 손 |
| bodyPart | string | upper_body/full_body | 움직임 영역 |
| emotion | string | happy/neutral/sad/surprised | 감정 (속도/에너지에 영향) |
| duration | float | 0.5~5.0 | 동작 길이 (초) |
| speed | float | 0.5~2.0 | 동작 속도 배수 |
| amplitude | float | 0.0~1.0 | 움직임 크기 (1.0 = 최대) |
| shoulderRaise | float | 0.0~1.0 | 어깨 올림 정도 |
| elbowBend | float | 0.0~1.0 | 팔꿈치 굽힘 정도 |
| wristFlip | float | 0.0~1.0 | 손목 회전 정도 |
| bodyLean | float | -0.5~0.5 | 상체 기울기 (앞/뒤) |
| headTilt | float | -0.3~0.3 | 고개 기울기 |
| rootMotion | bool | false | root bone 이동 여부 |
| feetPlanted | bool | true | 발 고정 여부 |
| loopable | bool | false | 루프 가능 여부 |

---

## 3. Gesture별 Control Rig 매핑

### wave

```text
사용 Control:
- right_hand_ik (또는 left_hand_ik)
- elbow_pole_vector_r
- shoulder_raise_r (추가 control)
- head_look (약간 대상 방향으로)
- spine_bend (bodyLean 반영)

동작 설계:
1. 팔 들기 (shoulder raise → elbow bend)
2. 손목 좌우 wrist flip (amplitude 기반 진폭)
3. speed 기반 반복 횟수 결정
4. duration 이후 팔 내리기 (ease out)
```

### point

```text
사용 Control:
- right_hand_ik (또는 left_hand_ik)
- elbow_pole_vector_r
- spine_bend (대상 방향으로 기울기)
- head_look (대상 방향)

동작 설계:
1. 팔 들어 대상 방향으로 뻗기
2. spine_bend로 상체를 약간 앞으로
3. head_look으로 시선 맞추기
4. 정지 유지 (duration)
5. 팔 내리기
```

### bow

```text
사용 Control:
- spine_bend (주요 제어)
- chest_twist (약간 forward)
- head_look (아래 방향)

동작 설계:
1. spine_bend + chest_twist로 상체 앞으로 굽히기
2. amplitude 기반 굽힘 각도 결정
3. 정지 (duration의 30%)
4. 천천히 복원
5. emotion에 따라 속도 조정 (happy → 가볍게, neutral → 정중하게)
```

### nod

```text
사용 Control:
- head_look (Y축: 위아래)

동작 설계:
1. head_look Y를 아래로 (amplitude 기반)
2. 복원
3. speed 기반 반복 횟수
4. duration 이내 완료
```

### explain

```text
사용 Control:
- right_hand_ik
- left_hand_ik
- elbow_pole_vector_r
- elbow_pole_vector_l
- spine_bend (앞으로 약간)
- chest_twist (좌우 교대)

동작 설계:
1. 양손을 앞으로 들어 설명하는 자세
2. 좌우 손을 교대로 amplitude 기반으로 움직임
3. chest_twist로 자연스러운 상체 움직임 추가
4. duration 기반으로 cycle 결정
```

---

## 4. Control Rig 구성 (Unreal)

### 필요 Control 목록

```text
right_hand_ik         ← 오른손 IK target
left_hand_ik          ← 왼손 IK target
elbow_pole_vector_r   ← 오른쪽 팔꿈치 방향
elbow_pole_vector_l   ← 왼쪽 팔꿈치 방향
head_look             ← 머리 회전 (LookAt)
spine_bend            ← 척추 굽힘 (전후)
chest_twist           ← 흉추 좌우 회전
shoulder_raise_r      ← 오른쪽 어깨 올림
shoulder_raise_l      ← 왼쪽 어깨 올림
```

### 캐릭터 고정 (1차)

```text
Unreal Manny (UE5 기본 캐릭터)
- 검증된 IK Rig 존재
- 기본 Control Rig 확장 가능
- MetaHuman 호환 가능성 높음
```

### Control Rig 구동 방식

```text
Option A: Blueprint Function Library
- JSON parameter → UFunction 호출
- Control Rig의 각 Control에 value set
- 간단하지만 animation curve 없이 즉시 pose만 적용

Option B: Control Rig Sequencer Track
- JSON parameter → Runtime Sequencer 생성
- curve 기반으로 부드러운 animation
- 복잡하지만 bake 품질이 좋음

Option C: Custom AnimNode
- JSON을 Animation Blueprint의 custom node로 처리
- runtime에서도 동작 가능
- 개발 공수 가장 높음

1차 MVP 권장: Option A로 빠르게 검증, 이후 Option B로 개선
```

---

## 5. LLM Prompt 설계

### System Prompt (영어)

```text
You are a motion parameter generator for a 3D animation system.
The user will describe a gesture in natural language.
You must output a JSON object that describes the gesture using the given schema.
Do NOT output bone rotations directly. Only output high-level gesture parameters.
Always ensure rootMotion is false and feetPlanted is true unless explicitly requested.
Keep duration between 0.5 and 4.0 seconds.
Output only valid JSON, no explanation.
```

### User Prompt 예시

```text
입력: "웃으면서 오른손으로 인사하듯 손 흔들어줘"

LLM 출력:
{
  "gesture": "wave",
  "hand": "right",
  "bodyPart": "upper_body",
  "emotion": "happy",
  "duration": 1.8,
  "speed": 1.2,
  "amplitude": 0.65,
  "shoulderRaise": 0.25,
  "elbowBend": 0.45,
  "wristFlip": 0.3,
  "bodyLean": 0.08,
  "headTilt": 0.05,
  "rootMotion": false,
  "feetPlanted": true,
  "loopable": false
}
```

```text
입력: "정중하게 허리 굽혀 인사해줘"

LLM 출력:
{
  "gesture": "bow",
  "hand": "none",
  "bodyPart": "upper_body",
  "emotion": "neutral",
  "duration": 2.5,
  "speed": 0.8,
  "amplitude": 0.7,
  "shoulderRaise": 0.0,
  "elbowBend": 0.0,
  "wristFlip": 0.0,
  "bodyLean": 0.6,
  "headTilt": -0.2,
  "rootMotion": false,
  "feetPlanted": true,
  "loopable": false
}
```

---

## 6. 장점과 한계

### 장점

```text
- API generation 비용이 거의 없음 (LLM만 사용)
- 즉시 preview 가능 (생성 대기 없음)
- 실패해도 비용 손실이 거의 없음
- runtime / editor 둘 다 확장 가능
- parameter 조정이 쉬움
- NPC gesture / 대화 시스템에 실무적으로 쓸 수 있음
- loopable이 필요한 idle 변형에 적합
```

### 한계

```text
- 진짜 text-to-motion AI generation은 아님
- Control Rig 품질에 크게 의존
- 복잡한 full-body motion은 부자연스러움
- gesture 종류를 직접 설계해야 함 (5~10개 수준이 현실적)
- 손가락 / 얼굴 표현 부족
- 걷기 / 뛰기 / 점프 불가 (1차)
```

---

## 7. Pipeline A / B-plain / B-enriched 비교 실험 계획

### 첫 실험 대상

```text
Gesture: friendly right-hand wave
Character: UE Manny
Duration: 1.5~2.0 sec
RootMotion: false
Feet: planted
Emotion: happy
Prompt: "웃으면서 오른손으로 인사하듯 손 흔들어줘"
```

### 세 결과물

```text
[A]          Pipeline A — Procedural JSON → Control Rig Preview
[B-plain]    원본 프롬프트 그대로 → T2M API → Generated FBX
[B-enriched] Procedural JSON → enriched prompt 변환 → T2M API → Generated FBX
```

### 비교 기준

```text
항목              | A (Procedural)    | B-plain (T2M)     | B-enriched (T2M)
생성 비용         | LLM만 ($0.001)    | Provider ($1~5)   | Provider ($1~5)
생성 시간         | 1~2초             | 5~30초            | 5~30초
UE 적용 시간      | 즉시              | Import/Retarget   | Import/Retarget
자연스러움        | 중간              | 중간~높음          | 높음 (기대)
gesture 정확도   | 높음 (설계된 것)   | 낮음~중간          | 높음 (기대)
발 고정 여부      | 완벽              | 검증 필요          | 검증 필요
Root drift        | 없음              | 검증 필요          | 검증 필요 (명시했으므로 낮을 것)
Skeleton 깨짐     | 없음              | Retarget 의존      | Retarget 의존
반복 안정성       | 높음              | 낮음               | 중간 (constraint 덕에 편차 줄어들 것)
파라미터 수정     | 쉬움              | 재생성 필요         | JSON 수정 후 재생성
라이선스 리스크   | 없음              | Provider 약관 의존  | Provider 약관 의존
```

### 검증하려는 가설

```text
Procedural JSON에서 추출한 enriched prompt가
단순 원본 프롬프트 대비 T2M API의 결과 품질을 개선한다.

구체적으로:
- gesture 종류와 body part가 명시되어 엉뚱한 동작이 줄어든다
- duration, speed, amplitude 제약으로 결과 편차가 줄어든다
- feetPlanted / rootMotion 명시로 foot sliding / root drift가 줄어든다
```

### 예상 결론

```text
단순 hand wave 기준:
- A가 비용/속도/안정성에서 유리
- B-enriched가 B-plain보다 gesture 정확도와 constraint 준수에서 유리
- B-enriched가 상용 T2M의 자연스러움을 살리면서 구조화된 결과를 낼 수 있는지가 핵심 검증 포인트
```
