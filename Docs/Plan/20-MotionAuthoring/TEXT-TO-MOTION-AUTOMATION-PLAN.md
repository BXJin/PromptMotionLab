# Text-to-Motion 자동화 적용 검토

작성일: 2026-05-02

이 문서는 Blue Garage `Software Engineer / 3D Graphics, Motion` 지원 적합도를 보강하기 위한 후속 실험 계획이다. 현재 프로젝트의 핵심 MVP는 `Unreal 전시 공간 + 모바일 패널 + 로컬 서버 + AI 전시 가이드`이며, text-to-motion은 MVP 필수 기능이 아니라 3D/Motion 역량을 더 강하게 보여주기 위한 확장 항목으로 분리한다.

## 1. 목표

사용자가 자연어로 원하는 제스처를 말하면, LLM이 이를 안전한 motion intent로 해석하고 Unreal 캐릭터가 해당 애니메이션을 재생하도록 만든다.

```text
사용자 입력: "웃으면서 손 흔들어줘"
LLM/Server: motionIntent = "ai_wave_happy", emotion = "happy"
Unreal: AI-generated animation asset 재생
```

핵심은 `실시간 생성` 자체가 아니라, `AI가 생성한 motion asset을 Unreal 실행 파이프라인에 연결했다`는 점이다.

## 2. 적용 범위

### 2.1 1차 적용: 오프라인 생성 + 수동/반자동 등록

가장 현실적인 방식이다.

```text
Text-to-motion 도구에서 모션 생성
-> FBX/BVH/GLB export
-> Unreal Editor import
-> IK Rig / IK Retargeter로 현재 캐릭터에 retarget
-> Animation Sequence 또는 Montage 생성
-> animation key registry에 등록
-> AI chat command로 재생
```

포트폴리오 기준으로는 이 정도만 구현해도 충분히 설득력이 있다. 기존 Mixamo/기본 애니메이션과 구분해 `AI-generated motion`으로 라벨링할 수 있기 때문이다.

### 2.2 2차 적용: import 자동화

가능하면 다음 단계를 자동화한다.

```text
GeneratedMotions/
  ai_wave_happy.fbx
  ai_bow_calm.fbx
  ai_explain_point.fbx

Unreal Editor Utility / Python:
  - 폴더 스캔
  - FBX import
  - 지정 skeleton에 animation import
  - naming convention 검증
  - registry JSON 갱신
```

이 방식은 `실시간 생성`은 아니지만, 제작자가 새 모션을 넣는 반복 작업을 줄여준다. 실무적으로도 더 안정적인 자동화다.

### 2.3 현재 비추천: 런타임 실시간 생성

아래 흐름은 현재 프로젝트 단계에서는 비추천이다.

```text
채팅 입력
-> text-to-motion 모델/API 호출
-> FBX 생성
-> packaged exe 런타임에서 import
-> retarget
-> 즉시 재생
```

이유:

- Unreal packaged runtime에서 FBX import/retarget은 에디터 파이프라인에 가깝다.
- 생성 시간과 품질이 일정하지 않다.
- skeleton mismatch, foot sliding, root motion 문제가 자주 생긴다.
- Steam 배포 기준으로 외부 API 비용/라이선스/네트워크 실패 문제가 생긴다.
- 시연 안정성이 떨어진다.

따라서 포트폴리오에서는 `runtime generation`보다 `offline generation + controlled runtime playback`이 더 적합하다.

## 3. 후보 도구

### DeepMotion SayMotion

장점:

- 텍스트 입력으로 3D animation 생성 가능
- FBX, GLB, BVH export 경로가 있어 Unreal 적용에 유리
- 웹 기반으로 빠르게 실험 가능

주의:

- API 자동화는 일반 공개 API처럼 바로 쓰기 어려울 수 있다.
- hand/face animation은 제한될 수 있다.
- generated motion의 품질 확인과 retarget 보정이 필요하다.

### Rokoko Text-to-Motion

장점:

- Rokoko Studio Preview에서 text-to-motion 생성 가능
- Unreal compatible skeleton export 흐름이 비교적 명확하다.
- FBX export 후 Unreal import 실험에 적합하다.

주의:

- 플랜/Preview 기능 제약이 있을 수 있다.
- 자동 API보다는 툴 기반 반자동 workflow에 가깝다.

### 로컬 MDM / MotionGPT 계열

장점:

- 연구/AI 역량 어필이 가장 강하다.
- HumanML3D, AMASS 같은 motion dataset 개념과 연결하기 좋다.
- 직접 inference pipeline을 구성하면 ML 이해도를 보여줄 수 있다.

주의:

- Windows/Unreal 연동 난이도가 높다.
- 기본 출력이 바로 UE용 FBX로 정리되는 상용툴 형태가 아닐 수 있다.
- SMPL/joint sequence -> BVH/FBX -> UE skeleton retarget 변환이 필요할 수 있다.
- GPU, Python 환경, dataset/model weight 관리가 필요하다.

## 4. 현재 프로젝트에 붙이는 구조

기존 AI chat 구조를 그대로 활용한다.

```text
Mobile Panel
-> ExhibitionServer /api/chat
-> ExhibitionAiGateway
-> LLM structured output
-> ExhibitionServer command validation
-> Unreal command dispatch
-> Character animation playback
```

추가되는 것은 animation key와 registry다.

```json
{
  "type": "playAnimation",
  "characterId": "Character_01",
  "animation": "ai_wave_happy"
}
```

허용 목록 예시:

```text
기존:
- wave
- bow
- clap
- explain
- idle

AI-generated:
- ai_wave_happy
- ai_bow_calm
- ai_explain_point
```

서버는 LLM이 임의의 animation 이름을 보내도 whitelist에 없는 값은 실행하지 않는다. 이 구조는 LLM command safety를 유지하면서 AI motion asset을 확장할 수 있다.

## 5. 추천 실험 세트

1. `ai_wave_happy`
   - Prompt: `A character smiles and waves hello in a friendly way.`
   - 연결 질문: "밝게 인사해줘"
   - 기대 command: `setEmotion happy` + `playAnimation ai_wave_happy`

2. `ai_bow_calm`
   - Prompt: `A character politely bows in a calm and respectful way.`
   - 연결 질문: "정중하게 인사해줘"
   - 기대 command: `setEmotion neutral` + `playAnimation ai_bow_calm`

3. `ai_explain_point`
   - Prompt: `A character explains an object with a small pointing gesture.`
   - 연결 질문: "이 전시물 설명해줘"
   - 기대 command: `playAnimation ai_explain_point`

4. `ai_surprise_react`
   - Prompt: `A character reacts with surprise and takes a small step back.`
   - 연결 질문: "놀라운 느낌으로 소개해줘"
   - 기대 command: `setEmotion surprise` + `playAnimation ai_surprise_react`

## 6. Role Fit 표현 방식

과장하면 안 되는 표현:

```text
실시간 text-to-motion generation을 구현했습니다.
```

현재 프로젝트에 맞는 정확한 표현:

```text
LLM이 사용자 자연어를 motion intent로 해석하고,
text-to-motion 도구로 생성한 animation asset을 Unreal 캐릭터의 안전한 animation command로 재생하는 구조를 설계했습니다.
```

구현 후 사용할 수 있는 표현:

```text
DeepMotion/Rokoko 기반으로 생성한 gesture animation을 FBX로 export하고,
Unreal IK Retargeter를 통해 프로젝트 캐릭터 skeleton에 맞춘 뒤,
AI chat의 structured command가 해당 animation key를 선택해 재생하도록 연결했습니다.
```

## 7. 우선순위

1. AI 전시 가이드 안정화
   - RAG 결과 품질
   - 전시물 metadata 확장
   - emotion/animation command mapping 안정화

2. 시연 품질 정리
   - 실제 노트북 패키징
   - 모바일 패널 접속
   - 전시물 3개 설명/분위기 변경/캐릭터 반응 영상 확보

3. Text-to-motion 1차 실험
   - `ai_wave_happy`, `ai_bow_calm`, `ai_explain_point` 3개 생성
   - Unreal retarget
   - chat command 연결

4. 자동화 보강
   - FBX import naming convention
   - animation registry JSON
   - command whitelist 확장

## 8. 결론

Text-to-motion은 적용 가능하다. 다만 현재 프로젝트에서는 `실시간 생성`보다 `오프라인 생성 asset을 AI chat command로 안전하게 재생`하는 방식이 맞다.

이 방식은 LLM Engineer와 3D/Motion 양쪽에 연결된다.

- LLM Engineer 관점: 자연어 intent parsing, structured output, command validation
- 3D/Motion 관점: generated motion asset, FBX import, IK retargeting, Unreal animation playback

따라서 이 기능은 MVP 본체가 아니라, Blue Garage role fit을 강화하는 후속 실험으로 분리해 진행한다.
---

## 9. 2026-05-03 추가 검토: JSON runtime motion vs editor pipeline

이 섹션은 현재 전시 프로젝트에 바로 붙이는 기능이 아니라, 별도 포트폴리오 MVP로 검토하는 `Prompt-to-Animation Unreal Tool` 방향을 정리한다.

핵심 질문:

```text
FBX/BVH export 없이, 프롬프트 입력 결과를 bone transform JSON으로 받아 Unreal에서 바로 재생할 수 있는가?
```

결론:

```text
가능은 하다.
하지만 full-body runtime generation을 메인 기능으로 삼기에는 품질/안정성 리스크가 크다.
실무형 포트폴리오로는 "Editor preview + bake" 구조가 더 적합하다.
```

### 9.1 bone JSON 방식은 가능한가

가능하다. motion service 또는 로컬 모델이 아래와 같은 frame별 bone transform을 반환하면 Unreal에서 이를 읽어 재생할 수 있다.

```json
{
  "skeleton": "UE_Manny",
  "fps": 30,
  "duration": 1.8,
  "space": "local",
  "tracks": {
    "upperarm_r": [
      { "time": 0.0, "rotation": [0.0, 0.0, 0.0, 1.0] },
      { "time": 0.5, "rotation": [0.1, 0.2, 0.0, 0.97] }
    ],
    "lowerarm_r": [
      { "time": 0.0, "rotation": [0.0, 0.0, 0.0, 1.0] },
      { "time": 0.5, "rotation": [0.2, 0.1, 0.0, 0.96] }
    ]
  }
}
```

Unreal 적용 후보:

- `UPoseableMeshComponent`
- Animation Blueprint의 `Transform Bone` 계열 노드
- Control Rig
- custom AnimNode
- Live Link 스타일의 runtime pose stream

다만 이 방식에서 어려운 부분은 JSON 생성 자체가 아니라, 생성된 transform이 실제 target skeleton에서 자연스럽게 재생되는지다.

문제 지점:

- bone 이름/계층 불일치
- source skeleton과 target skeleton의 rest pose 차이
- local/component/world space 혼동
- quaternion continuity 문제
- 관절 제한 위반
- root motion과 foot contact 문제
- idle/montage/upper-body mask와의 blend 문제
- packaged runtime에서 debugging과 보정이 어렵다는 점

따라서 `손 흔들기`, `고개 끄덕이기`, `상체 설명 제스처`, `가리키기` 같은 upper-body gesture는 JSON runtime playback MVP가 가능하다. 반대로 `걷기`, `달리기`, `점프`, `춤`, `앉기/일어서기` 같은 full-body locomotion은 foot sliding, root motion, retargeting 때문에 난이도가 급격히 올라간다.

### 9.2 LLM이 bone JSON을 직접 만들게 하는 것은 적합한가

LLM이 JSON 문법을 만드는 것은 가능하다. 하지만 LLM이 수십 개 bone의 quaternion을 30fps로 생성하고, 그 결과가 target character에서 자연스럽게 재생되기를 기대하는 구조는 위험하다.

더 좋은 역할 분리는 다음과 같다.

```text
LLM
-> 사용자의 자연어를 motionIntent / style / constraint로 정규화

Motion Generator / IK Solver
-> 실제 pose sequence 또는 bone transform 생성

Motion Validator
-> skeleton compatibility, joint limit, foot contact, continuity 검사

Unreal
-> preview, retarget, bake 또는 runtime playback
```

권장 LLM 출력 예:

```json
{
  "motionIntent": "greeting_wave",
  "style": "friendly",
  "bodyPart": "upper_body",
  "hand": "right",
  "duration": 1.8,
  "constraints": {
    "rootMotion": false,
    "keepFeetPlanted": true,
    "loopable": false
  }
}
```

즉, LLM은 `motion director`, motion model/solver는 `animator`, Unreal plugin은 `preview and bake tool`로 보는 것이 맞다.

### 9.3 runtime에서 즉시 보고 싶을 때 가능한 방식

#### 방식 A: 기존 animation 선택

```text
Prompt
-> LLM intent 분석
-> wave / bow / explain 같은 기존 animation 선택
-> 즉시 재생
```

가장 안정적이지만 새 motion generation은 아니다.

#### 방식 B: Control Rig parameter playback

```text
Prompt
-> LLM이 gesture parameter 생성
-> Control Rig / AnimBP가 팔, 머리, 상체를 procedural하게 움직임
```

예:

```json
{
  "motionType": "wave",
  "hand": "right",
  "amplitude": 0.65,
  "speed": 1.1,
  "duration": 1.8,
  "emotion": "happy"
}
```

runtime MVP로는 가장 추천한다. 데이터가 작고, 안정적이며, LLM과 잘 맞는다.

#### 방식 C: bone JSON sequence playback

```text
Prompt
-> motion generator가 bone transform JSON 생성
-> Unreal runtime이 frame별 pose 적용
```

상체 gesture MVP로는 가능하다. full-body는 난이도가 높다.

#### 방식 D: runtime AnimSequence 생성

```text
Prompt
-> motion sequence 생성
-> packaged runtime에서 AnimSequence 생성
-> 재생
```

비추천한다. 에디터 전용 animation data API, asset 저장, compression, retargeting 제약 때문에 runtime보다는 editor tool에 적합하다.

### 9.4 Editor Plugin preview + bake가 더 실무적인 이유

Editor Plugin에서는 target character의 `USkeleton`, `USkeletalMesh`, bone hierarchy를 읽고, 생성된 motion을 현재 프로젝트 캐릭터 기준으로 검증할 수 있다.

가능한 workflow:

```text
1. Unreal Editor에서 character 선택
2. Prompt 입력
3. LLM이 motionIntent와 constraint 생성
4. motion provider가 JSON/BVH/FBX/pose sequence 생성
5. plugin이 source skeleton과 target skeleton 비교
6. viewport에서 즉시 preview
7. 문제 리포트
   - missing bone
   - extreme rotation
   - root drift
   - foot sliding
   - duration mismatch
   - loopable 여부
8. 사용자 approve/reject
9. approve된 결과를 AnimSequence로 bake
10. metadata와 embedding을 저장
```

이 방식이 runtime보다 좋은 이유:

- 실패해도 게임 실행 흐름을 망치지 않는다.
- retarget pose, IK Rig, Control Rig, Animation Modifier 같은 에디터 도구를 쓸 수 있다.
- 생성 결과를 눈으로 보고 승인한 뒤 asset으로 저장할 수 있다.
- 저장된 AnimSequence는 이후 runtime에서 일반 UE animation처럼 안정적으로 재생된다.

권장 포트폴리오 이름:

```text
Prompt-to-Animation Unreal Editor Tool
```

핵심 어필:

```text
AI가 생성한 motion을 바로 runtime에 던지는 것이 아니라,
Unreal Editor 안에서 target character 기준으로 preview, validate, approve, bake하는 제작 파이프라인을 구현한다.
```

### 9.5 Vector DB 적용 방향

Vector DB는 motion을 직접 생성하지 않는다. 대신 승인된 motion과 요청 프롬프트를 의미 기반으로 저장하고, 다음 요청에서 재사용/추천/생성 보조에 활용한다.

저장 대상:

```text
prompt
normalizedIntent
motion description
tags
skeleton
asset path
quality metadata
approval status
```

예:

```json
{
  "id": "motion_wave_friendly_001",
  "prompt": "친근하게 손 흔드는 인사 모션",
  "normalizedIntent": "greeting_wave_friendly",
  "embeddingText": "friendly upper-body right-hand wave greeting while standing still",
  "motionAssetPath": "/Game/GeneratedAnimations/Wave_Friendly_001",
  "motionJsonPath": "/GeneratedMotions/wave_friendly_001.json",
  "skeleton": "UE_Manny",
  "duration": 1.8,
  "tags": ["wave", "greeting", "friendly", "upper_body"],
  "quality": {
    "approved": true,
    "rating": 4.5,
    "footSliding": "none",
    "loopable": false
  }
}
```

검색 흐름:

```text
새 prompt
-> embedding
-> Vector DB에서 유사한 approved motion 검색
-> 있으면 재사용/추천
-> 없으면 새 motion 생성
-> 사용자가 approve하면 metadata + embedding 저장
```

주의:

- bone transform 숫자 배열 전체를 embedding하는 것이 아니다.
- motion의 의미 설명, intent, tag, 품질 metadata를 embedding/search 대상으로 삼는다.

활용 효과:

- 비슷한 prompt에 대해 검증된 motion 재사용
- 생성 비용 절감
- 팀/프로젝트 style consistency 유지
- rejected motion도 저장해 비슷한 실패 반복 방지
- retrieval-augmented motion generation 가능

### 9.6 기존 상용 도구와 차별화

이미 존재하는 계열:

- Rokoko Text-to-Motion
- DeepMotion SayMotion
- nocapmocap
- Kimodo / Kimodo Motion Studio
- MotoricaStudio UE plugin
- Mixamo retargeting plugin
- Rokoko / Shadow mocap Unreal plugin

따라서 `Prompt -> animation 생성`만 구현하면 차별성이 약하다.

차별화 방향은 다음이다.

```text
Prompt
-> motion intent normalization
-> approved motion Vector DB 검색
-> 유사 motion 재사용 또는 새 생성
-> target skeleton compatibility 검사
-> viewport preview
-> quality validation
-> approve/reject
-> AnimSequence bake
-> metadata + embedding 저장
-> 다음 생성 품질 개선
```

이 방향은 단순 text-to-motion 생성기가 아니라 다음에 가깝다.

```text
AI Motion Pipeline / Motion Asset QA Tool for Unreal
```

포트폴리오에서 강조할 점:

- LLM prompt normalization
- Vector DB 기반 approved motion retrieval
- motion metadata schema
- Unreal skeleton validation
- preview/bake workflow
- quality feedback loop

### 9.7 별도 MVP 제안

현재 전시 프로젝트와 분리해서 별도 MVP로 만든다면 다음 범위가 적합하다.

1차 MVP:

```text
UE Editor Plugin
- prompt input
- selected character skeleton read
- motion provider mock 또는 simple procedural generator
- JSON pose preview
- approve/reject
- bake metadata 저장
```

2차 MVP:

```text
- external text-to-motion provider 연동
- generated motion JSON/FBX/BVH 수신
- target skeleton validation
- AnimSequence bake
```

3차 MVP:

```text
- Vector DB approved motion search
- rejected motion memory
- quality scoring
- similar prompt reuse
```

runtime 실험은 별도 optional로 둔다.

```text
Prompt
-> LLM parameter JSON
-> Control Rig upper-body gesture
```

이 정도면 runtime에서도 "프롬프트 입력 후 캐릭터가 바로 움직인다"를 보여줄 수 있고, full-body generation 리스크는 피할 수 있다.

---

## 10. 2026-05-03 정정: text-to-motion의 핵심은 새 motion generation

앞선 검토에서 Vector DB retrieval을 1차 MVP처럼 설명한 부분은 목적과 다르다. text-to-motion의 핵심은 기존 motion 검색이 아니라, 사용자의 자연어 prompt로 **새로운 motion sequence를 생성**하는 것이다.

따라서 별도 포트폴리오 MVP의 핵심 목표는 다음으로 수정한다.

```text
Prompt
-> text-to-motion model/API
-> new motion sequence generation
-> Unreal Editor에서 target character 기준 preview
-> approve
-> AnimSequence bake
```

Vector DB는 핵심 생성 엔진이 아니라 후속 최적화 계층이다.

```text
1차 핵심: 새 motion 생성
후속 확장: approved motion 저장, 유사 prompt 참고, 중복 생성 방지, 품질 관리
```

### 10.1 수정된 MVP 정의

MVP 이름:

```text
Prompt-to-New-Motion Unreal Editor Tool
```

성공 기준:

```text
1. UE Editor Plugin에서 prompt 입력
2. Motion Generation Server가 text-to-motion model/API 호출
3. 기존 animation clip 검색이 아니라 새로운 motion 생성
4. 생성 결과를 JSON/BVH/FBX 중 하나로 UE Plugin에 전달
5. UE Editor viewport에서 target character로 preview
6. approve 시 AnimSequence로 bake
```

MVP에서 제외:

- Vector DB 기반 approved motion retrieval
- multi-user workflow
- runtime full-body generation
- MCP 기반 editor automation
- Steam packaged runtime generation

MVP 이후 확장:

- Vector DB로 approved motion metadata 저장
- rejected motion memory
- quality scoring
- prompt/model/version별 evaluation
- MCP tool로 UE Editor 작업 자동화
- runtime upper-body procedural gesture

### 10.2 권장 아키텍처

```text
[Unreal Editor Plugin]
  - prompt input
  - selected character skeleton read
  - preview viewport / preview actor
  - generated motion import/preview
  - approve/reject UI
  - bake to AnimSequence
        |
        v
[Motion Generation Server]
  - request validation
  - prompt normalization
  - model/provider routing
  - generation job queue
  - post-processing
  - output conversion
        |
        +--> [LLM Provider]
        |      - prompt cleanup
        |      - motion intent / constraints
        |
        +--> [Text-to-Motion Provider]
        |      - local model or commercial API
        |
        +--> [Storage]
               - generated JSON/BVH/FBX
               - preview files
               - logs
```

핵심 데이터 흐름:

```text
1. 사용자가 "A character smiles and waves hello with the right hand" 입력
2. Plugin이 selected skeleton 정보와 함께 서버에 요청
3. LLM이 prompt를 motion generation에 적합한 영어 prompt/constraint로 정규화
4. text-to-motion model/API가 새 motion 생성
5. 서버가 결과를 UE preview 포맷으로 변환
6. Plugin이 target character에 preview
7. 사용자가 approve
8. Plugin이 AnimSequence로 bake
```

### 10.3 기술 스택 정리

#### Unreal Editor Plugin

권장:

- Unreal Engine 5 C++ Editor Plugin
- Slate 또는 Editor Utility Widget
- `USkeletalMesh`, `USkeleton` 분석
- preview actor / preview scene
- HTTP client
- JSON parser
- generated motion preview player
- AnimSequence bake 기능

선택:

- Control Rig
- IK Rig / IK Retargeter
- Animation Modifier
- Python Editor Script

역할:

```text
UE project 안에서 target character를 기준으로 generated motion을 확인하고 저장하는 제작 도구
```

#### Motion Generation Server

권장:

- Python FastAPI
- Pydantic schema validation
- background job queue
- file storage
- provider abstraction

이유:

- text-to-motion 모델 대부분이 Python/PyTorch 생태계에 있다.
- BVH/SMPL/joint sequence 변환 라이브러리도 Python 쪽이 편하다.
- GPU 서버로 분리하기 쉽다.

대안:

- ASP.NET Core Gateway + Python Worker

이 경우:

```text
ASP.NET Core
-> auth / project API / metadata 관리
Python Worker
-> actual model inference / motion conversion
```

#### LLM Provider

역할:

- 사용자의 자연어를 text-to-motion model에 적합한 prompt로 정리
- duration, style, body part, root motion 여부 같은 constraint 생성

후보:

- OpenAI
- Gemini
- Claude
- local LLM

예상 출력:

```json
{
  "generationPrompt": "A friendly standing character smiles and waves hello with the right hand. Upper body gesture, feet planted.",
  "style": "friendly",
  "durationSeconds": 2.0,
  "bodyPart": "upper_body",
  "rootMotion": false,
  "constraints": ["feet_planted", "right_hand_wave"]
}
```

#### Text-to-Motion Provider

후보 1: 상용/서비스 API

- DeepMotion SayMotion
- Rokoko Text-to-Motion
- Kimodo
- nocapmocap
- Rigtix

장점:

- 빠른 실험
- 모델 학습/서빙 부담이 적음
- FBX/BVH/GLB output 가능성이 높음

단점:

- API 제공 여부와 자동화 범위가 서비스마다 다름
- 비용/라이선스 제약
- output skeleton/control이 제한될 수 있음

후보 2: 로컬/자가 호스팅 모델

- MDM
- MotionDiffuse
- T2M-GPT
- MotionGPT
- Hunyuan Motion / HY-Motion 계열

장점:

- 실제 ML pipeline 어필이 강함
- model inference, post-processing, conversion까지 설명 가능
- 비용을 서버 자원 중심으로 예측 가능

단점:

- GPU 필요 가능성 큼
- Windows/UE 연동 난이도 높음
- output을 UE skeleton에 맞추는 변환 작업이 필요
- 품질 편차가 큼

#### Motion Format

preview 후보:

- JSON bone transform sequence
- BVH
- GLB animation
- FBX

권장 전략:

```text
Preview 빠른 반복: JSON 또는 BVH
최종 저장: AnimSequence bake
외부 도구 호환: FBX/BVH/GLB import/export
```

JSON은 UE Plugin과 서버 사이의 내부 preview format으로 좋다. 하지만 최종 결과는 UE `AnimSequence`로 bake하는 것이 실무적이다.

#### Storage / Metadata

MVP:

- local folder storage
- SQLite
- JSON metadata file

확장:

- PostgreSQL
- S3-compatible object storage
- Qdrant / Chroma / pgvector

Vector DB는 MVP 핵심이 아니라 2차 확장이다.

### 10.4 비용 산정

비용은 어떤 provider를 쓰느냐에 따라 크게 달라진다. 아래는 포트폴리오 MVP 기준의 현실적인 범위다.

#### 옵션 A: 상용 text-to-motion 서비스 사용

구성:

```text
UE Plugin
-> FastAPI Gateway
-> commercial motion generation API
```

비용 요소:

- 서비스 구독료
- 생성 횟수 제한
- export 기능 유료 여부
- API 자동화 가능 여부

예상:

```text
초기 MVP: 월 0~50 USD 범위에서 실험 가능할 가능성 있음
자동화/API 사용: 서비스 정책에 따라 월 20~200 USD 이상 가능
```

주의:

- 웹 UI만 제공하고 공식 API가 없으면 완전 자동화가 어렵다.
- 무료/체험 플랜은 상업적 사용, export, batch generation에 제한이 있을 수 있다.

#### 옵션 B: 로컬 PC GPU 사용

구성:

```text
UE Plugin
-> local FastAPI server
-> local PyTorch text-to-motion model
```

비용 요소:

- 직접 GPU 보유 시 API 비용은 거의 없음
- 전기료/환경 구축 시간
- 모델 weight/dataset 관리

예상:

```text
금전 비용: 낮음
개발 시간 비용: 높음
리스크: 높음
```

적합한 경우:

- ML pipeline 자체를 강하게 어필하고 싶을 때
- 로컬 LLM/로컬 AI 포트폴리오로 확장하고 싶을 때

#### 옵션 C: 클라우드 GPU 서버 사용

구성:

```text
UE Plugin
-> cloud motion generation server
-> GPU inference
```

비용 요소:

- GPU instance 시간당 비용
- storage
- bandwidth
- idle 비용

대략적인 판단:

```text
T4/L4급 GPU를 필요할 때만 켜면 실험 비용은 관리 가능
상시 운영하면 포트폴리오 개인 프로젝트에는 부담 큼
```

운영 전략:

```text
개발/촬영 때만 GPU 서버 실행
평소에는 서버 중지
생성 결과는 저장해서 재사용
```

#### 옵션 D: 하이브리드

추천 현실안:

```text
1. MVP 초반: 상용 서비스 또는 mock/procedural generator로 UE Plugin workflow 완성
2. 이후: 로컬/클라우드 text-to-motion 모델 1개 붙이기
3. 생성 결과는 저장해서 반복 비용 줄이기
```

이 방식이 가장 균형이 좋다.

### 10.5 MCP 위치 재정리

MCP는 text-to-motion의 필수 요소가 아니다.

필수:

```text
UE Plugin
Motion Generation Server
Text-to-Motion Model/API
Motion Preview/Bake
```

선택:

```text
MCP
-> LLM agent가 UE Editor 기능을 tool call로 조작하게 할 때 사용
```

예:

```text
Agent:
  "현재 선택된 캐릭터 skeleton 읽어줘"
  "프리뷰 액터 생성해줘"
  "이 motion을 AnimSequence로 bake해줘"

MCP tool:
  get_selected_skeleton()
  preview_motion()
  bake_anim_sequence()
```

하지만 1차 MVP에서는 MCP를 넣지 않는 편이 낫다. Plugin이 직접 서버를 호출하고 직접 preview/bake하는 구조가 더 단순하고 제품형이다.

### 10.6 최종 권장 MVP 범위

1차:

```text
Prompt-to-New-Motion Editor Preview

- UE Editor Plugin
- prompt 입력
- selected character skeleton 정보 수집
- FastAPI Motion Generation Server
- text-to-motion provider 1개 연동
- generated motion preview
- approve/reject
- AnimSequence bake
```

2차:

```text
Motion quality validation

- missing bone check
- duration check
- root drift check
- extreme rotation check
- foot sliding heuristic
```

3차:

```text
Motion memory / Vector DB

- approved motion metadata 저장
- rejected result 저장
- similar prompt 검색
- prompt/model/version별 품질 비교
```

4차:

```text
MCP editor automation

- LLM agent가 UE Plugin 기능을 tool로 호출
- skeleton 분석, preview, bake를 자동화
```

### 10.7 포트폴리오 표현

정확한 표현:

```text
Unreal Editor Plugin에서 자연어 prompt를 입력하면, Motion Generation Server가 text-to-motion model/API를 호출해 새로운 motion sequence를 생성하고, 이를 target character 기준으로 preview한 뒤 AnimSequence로 bake하는 AI-assisted animation authoring pipeline을 설계했습니다.
```

강조할 수 있는 기술:

- text-to-motion generation
- Unreal Editor Plugin
- target skeleton analysis
- motion format conversion
- preview/bake workflow
- prompt normalization
- model/provider abstraction
- motion validation

피해야 할 표현:

```text
Vector DB로 text-to-motion을 구현했다.
LLM만으로 full-body bone animation을 생성했다.
runtime에서 안정적인 full-body motion generation을 완성했다.
```
