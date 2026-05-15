# AI Motion Generation Pipeline for Unreal — 기획/기술 정리

## 0. 한 줄 요약

사용자가 Unreal Engine 플러그인에서 자연어 프롬프트를 입력하면, 서버가 모션 생성 API 또는 로컬 모델을 통해 3D 애니메이션을 생성하고, Unreal Editor 안에서 선택된 캐릭터에 자동으로 Import / Retarget / Preview / Bake 하는 **AI Motion Generation Pipeline SaaS**를 만든다.

---

## 1. 아이디어의 핵심

### 사용자가 원하는 경험

```text
Unreal Editor 플러그인 설치
→ Skeletal Mesh 또는 캐릭터 선택
→ 프롬프트 입력
   예: "점프하면서 두 손을 흔들며 반기는 애니메이션 만들어줘"
→ 서버가 요청 분석
→ DeepMotion 같은 Text-to-Motion API 호출
→ 결과 모션 수신
→ Unreal Editor 안에서 Preview
→ 마음에 들면 Bake to Animation Sequence
```

### 서비스 포지션

이 서비스는 단순한 "모션 라이브러리"가 아니다.

```text
모션 라이브러리 = 이미 만들어진 FBX/BVH/Animation Asset을 구매해서 쓰는 것
AI Motion Generation = 프롬프트로 새로운 모션을 생성하는 것
```

따라서 현재 아이디어의 본질은 다음에 가깝다.

```text
Text-to-Motion Middleware
Prompt-to-Animation SaaS
AI Motion Bridge for Unreal
AI Motion Generation Pipeline
```

---

## 2. 왜 Unreal 플러그인인가?

기존 서비스들은 보통 다음 흐름이다.

```text
웹/스튜디오에서 모션 생성
→ FBX/BVH 다운로드
→ Unreal에 수동 Import
→ 수동 Retarget
→ Preview
→ 필요하면 Bake
```

이 과정은 개발자 입장에서 번거롭다.

이 서비스는 그 과정을 Unreal Editor 내부에서 자동화한다.

```text
캐릭터 선택
→ 프롬프트 입력
→ 생성 요청
→ 결과 수신
→ 자동 Import
→ 자동 Retarget
→ Preview
→ Bake
```

즉 차별점은 **모션 생성 모델 자체**보다 **실제 개발 워크플로우 자동화**에 있다.

---

## 3. DeepMotion 기준 서비스 흐름

### 기본 구조

```text
User / Unreal Plugin
        ↓
ASP.NET Core Server
        ↓
Motion Provider Layer
        ↓
DeepMotion SayMotion API
        ↓
Generated Motion Result
        ↓
Server Storage
        ↓
Unreal Plugin Import / Retarget / Preview / Bake
```

### 세부 흐름

```text
1. 사용자가 Unreal 플러그인에서 프롬프트 입력
2. 선택된 Skeletal Mesh / Skeleton 메타데이터 추출
3. 서버로 prompt + character metadata 전송
4. 서버에서 프롬프트 번역/정규화
5. DeepMotion API 호출
6. 결과 FBX/BVH/GLB/JSON 수신
7. 서버에 사용자 전용 저장
8. UE 플러그인으로 결과 전달
9. Unreal에서 자동 Import
10. IK Retargeter 또는 Retarget Preset 적용
11. Preview
12. Bake to Animation Sequence
```

---

## 4. Skeletal Mesh를 같이 보내면 품질이 좋아지나?

### 결론

좋아질 가능성이 크다.  
하지만 정확히는 **모션 생성 품질**이 좋아지는 것이 아니라 **리타겟 품질**이 좋아지는 쪽에 가깝다.

```text
Skeletal Mesh 분석
= 캐릭터에 덜 깨지게 적용하기 위한 정보

Prompt 해석 / 동작 생성 품질
= DeepMotion 또는 로컬 모델의 생성 품질
```

### Skeletal Mesh 분석으로 개선 가능한 것

```text
- Humanoid 여부 판단
- Bone hierarchy 분석
- Root bone / pelvis / spine / arm / leg 구조 확인
- Manny / MetaHuman / Mixamo / Custom Skeleton 분류
- A-Pose / T-Pose 여부 추정
- IK Rig / Control Rig 존재 여부 확인
- Retargeter 자동 생성 가능성 판단
- Scale / orientation 문제 사전 경고
```

### 그래도 남는 문제

```text
- 발 미끄러짐
- 착지 타이밍 이상
- 팔이 몸을 뚫음
- 손가락/얼굴 표현 부족
- Root Motion 불안정
- 캐릭터 체형 차이
- 오브젝트 상호작용 부족
```

따라서 품질 개선의 핵심은 단순히 Mesh를 서버에 올리는 것이 아니라 다음 전체 파이프라인이다.

```text
캐릭터 검사
→ Skeleton preset 분류
→ DeepMotion custom character upload 여부 판단
→ UE IK Retargeter 적용
→ foot/root/contact 보정
→ Preview
→ Bake
```

---

## 5. 캐시와 라이선스 이슈

### 사용자가 생각한 구조

```text
사용자 A가 프롬프트 요청
→ 서버가 DeepMotion으로 모션 생성
→ 결과를 서버에 저장
→ 사용자 B가 같은 요청
→ DeepMotion 재호출 없이 A의 결과물을 B에게 제공
```

### 기술적으로는 가능하지만 법적으로 위험

이 구조는 DeepMotion 결과물을 네 서버의 공용 자산처럼 재사용하는 형태가 된다.

문제는 다음이다.

```text
A에게 전달하기 위한 임시 저장 / 개인 캐시
= API 중개 구조상 자연스러움

A 결과물을 B에게 다시 제공
= 에셋 재배포 / stand-alone asset access 제공으로 해석될 수 있음
```

### 안전한 구조

```text
User Private Cache
- A가 만든 결과물은 A만 재사용
- 같은 프롬프트를 A가 다시 요청하면 기존 결과 반환
- B에게는 보여주지 않음
```

### 위험한 구조

```text
Global Shared Cache
- A가 생성한 FBX/BVH/Animation Asset을 서버에 저장
- B/C/D 사용자에게도 Preview / Download / Bake 제공
```

이 경우 DeepMotion 약관 또는 API 계약에 걸릴 가능성이 높다.

### 공용으로 재사용하기 상대적으로 안전한 데이터

```text
- 원본 프롬프트
- 번역/정규화된 프롬프트
- tags
- duration
- root motion 여부
- skeleton preset
- quality score
- 실패/성공 로그
- 추천 파라미터
```

### 공용 재사용이 위험한 데이터

```text
- FBX
- BVH
- GLB
- Animation Sequence
- Retargeted Animation Asset
```

---

## 6. 모션 라이브러리와 Motion Generation의 차이

### 모션 라이브러리

MoCap Online, ActorCore, Mixamo, Fab Animation Pack 같은 것은 대부분 이미 만들어진 애니메이션 에셋이다.

```text
Walk
Run
Jump
Attack
Wave
Idle
Dance
Sit
Reload
```

즉 이것들은 **생성 AI**가 아니라 **이미 존재하는 모션 재고**에 가깝다.

### Motion Generation

DeepMotion SayMotion, MDM, MLD, MotionLCM 같은 것은 프롬프트나 조건으로 모션을 생성하는 쪽이다.

```text
Prompt
→ AI Model / API
→ New Motion
```

따라서 현재 만들고 싶은 서비스에는 DeepMotion / MDM 계열이 더 맞다.

---

## 7. DeepMotion과 로컬 모델의 역할

### DeepMotion

초기 MVP에 적합하다.

```text
장점:
- 상용 품질 기대 가능
- Text-to-Motion 방향에 맞음
- FBX/BVH/GLB export 가능
- 포트폴리오에서 실무형 API 연동으로 설명 가능

단점:
- API 접근은 별도 신청 또는 계약 필요 가능성
- 결과물 공용 재사용은 라이선스 리스크
- 호출당 비용 발생
```

### MDM / MLD / MotionLCM 계열

장기 확장용이다.

```text
장점:
- 로컬 Provider로 확장 가능
- API 비용 절감 가능성
- 자체 생성 결과물 기반 공용 캐시 가능성

단점:
- UE Animation Sequence로 바로 나오지 않음
- SMPL/HumanML3D 계열 표현을 UE Skeleton으로 변환해야 함
- Foot sliding / root motion / retarget 품질 문제가 큼
- GPU 서버 필요
- 라이선스 검토 필요
```

---

## 8. Local Provider가 어려운 이유

단순히 "하나 뽑는 것"은 가능할 수 있다.

문제는 뽑힌 결과를 Unreal에서 바로 쓸 수 있는 형태로 변환하는 과정이다.

### 로컬 모델 출력 형태

```text
- joint position array
- SMPL / SMPL-X pose
- HumanML3D motion representation
- numpy file
- visualization mp4
```

### Unreal이 원하는 형태

```text
- UE Skeleton 기준 Animation Sequence
- FBX Animation
- frame별 bone transform
- root / pelvis / spine / arm / leg rotation
- Retarget 가능한 hierarchy
```

### 필요한 변환 과정

```text
로컬 모델 출력
→ joint position / SMPL pose 해석
→ bone rotation 계산
→ skeleton hierarchy 매핑
→ root motion 계산
→ FBX/BVH export
→ Unreal import
→ IK Retarget
→ Preview
→ Bake
```

따라서 어려운 이유는 컴퓨터 사양만이 아니다.

```text
1. 모델 실행 환경
2. 출력 포맷 변환
3. Skeleton mapping
4. UE Retarget pipeline
5. 발 미끄러짐 보정
6. 상용 라이선스 검토
7. 서비스 품질 안정화
```

---

## 9. 비용 구조

비용은 크게 세 부분이다.

```text
1. DeepMotion 모션 생성 비용
2. 프롬프트 보정용 LLM 비용
3. 서버 / 스토리지 / 트래픽 비용
```

### DeepMotion 비용

핵심 비용이다.

```text
DeepMotion API 또는 SayMotion credit
= 모션 생성 원가의 대부분
```

포트폴리오 단계에서는 수십 회 정도만 생성하면 되므로 부담이 크지 않을 가능성이 높다.  
다만 실제 API 자동 호출은 Client ID / Client Secret 또는 API Access가 필요할 수 있다.

### 프롬프트 보정 AI 비용

상대적으로 매우 작다.

예:

```text
입력:
"점프하면서 두 손을 흔들며 반기는 애니메이션 만들어줘"

정규화:
"A cheerful full-body humanoid character jumps once and waves both hands enthusiastically as a greeting. Keep the motion short, natural, and game-ready."
```

이 정도 번역/정규화는 저가 LLM을 쓰면 비용 부담이 거의 없다.

### 서버/스토리지 비용

초기에는 작다.

```text
- FBX/BVH 저장
- Job status 관리
- 다운로드 트래픽
- 사용자 private cache
```

실제 사용자가 많아지면 트래픽과 저장소 정책이 중요해진다.

---

## 10. API 계약이 지금 필요한가?

### 포트폴리오 기준 결론

처음부터 API 계약까지 할 필요는 거의 없다.

### 추천 방식

```text
DeepMotion 웹에서 수동으로 모션 생성
→ FBX/BVH/GLB 다운로드
→ 네 서버 storage에 저장
→ UE 플러그인이 서버에서 결과를 받은 것처럼 처리
→ Import / Retarget / Preview / Bake 자동화
```

이 방식만으로도 포트폴리오 핵심은 충분히 보여줄 수 있다.

### 포트폴리오 설명 문구

```text
현재 MVP는 DeepMotion/SayMotion 결과물을 서버에서 수신한 것으로 가정한 비동기 Job Pipeline을 구현했습니다.
MotionProvider 인터페이스를 통해 실제 API Provider와 Mock/Manual Provider를 분리했으며,
DeepMotion API Key 발급 시 Provider만 교체하여 실시간 생성 호출로 확장할 수 있습니다.
```

---

## 11. 추천 아키텍처

### Motion Provider 구조

```text
IMotionProvider
├─ MockMotionProvider
├─ DeepMotionManualProvider
├─ DeepMotionApiProvider
├─ UserPrivateCacheProvider
├─ LocalMDMProvider
└─ LicensedLibraryProvider
```

### 각 Provider 역할

```text
MockMotionProvider
- 미리 준비한 샘플 FBX/BVH 반환
- API 없이 MVP 개발 가능

DeepMotionManualProvider
- DeepMotion 웹에서 수동 생성한 결과를 서버에 업로드
- 실제 API 결과처럼 UE 플러그인에 반환

DeepMotionApiProvider
- 나중에 API Access / Client Secret 확보 시 실제 호출

UserPrivateCacheProvider
- 같은 사용자의 같은 요청은 기존 결과 재사용

LocalMDMProvider
- 나중에 MDM/MLD/MotionLCM 같은 로컬 모델 연결

LicensedLibraryProvider
- 별도 라이선스를 확보한 모션 에셋 검색/제공
```

---

## 12. MVP 범위 추천

### MVP에서 반드시 보여줄 것

```text
1. Unreal Editor Plugin UI
2. Prompt 입력
3. 서버 Job 생성
4. Job 상태 조회
5. 결과 모션 다운로드
6. Content Browser 자동 Import
7. 선택 캐릭터 기준 Retarget
8. Preview
9. Bake to Animation Sequence
10. 사용자 private cache
```

### MVP에서 욕심내지 말 것

```text
1. DeepMotion 공식 API 계약
2. 공용 모션 캐시
3. 모든 Skeleton 자동 완벽 대응
4. Local MDM 완전 통합
5. 상용 품질의 motion editing
6. 다중 캐릭터 / 오브젝트 상호작용
```

---

## 13. 포트폴리오 단계별 로드맵

### Phase 1 — Mock / Manual Pipeline

목표:

```text
API 없이도 전체 파이프라인을 검증한다.
```

구현:

```text
- UE 플러그인 UI
- ASP.NET Core 서버
- Job API
- 미리 저장된 FBX/BVH 반환
- UE 자동 Import
- Retarget
- Preview
- Bake
```

---

### Phase 2 — DeepMotion 연동 준비

목표:

```text
DeepMotion API를 붙일 수 있는 구조를 만든다.
```

구현:

```text
- IMotionProvider 인터페이스
- DeepMotionManualProvider
- DeepMotionApiProvider stub
- prompt normalization
- private cache
- job status 관리
```

---

### Phase 3 — Skeletal Mesh 분석

목표:

```text
리타겟 품질을 높인다.
```

구현:

```text
- Skeleton hierarchy 추출
- Manny / MetaHuman / Mixamo preset 판별
- root bone / pelvis / spine / limbs 매핑
- IK Rig 존재 여부 확인
- Control Rig 존재 여부 확인
- 문제점 리포트 표시
```

---

### Phase 4 — Metadata Search / Vector DB

목표:

```text
생성 성공률을 높이고 불필요한 API 호출을 줄인다.
```

구현:

```text
- prompt normalization 저장
- tags 저장
- duration/root motion/quality score 저장
- 실패/성공 로그 저장
- 유사 요청 검색
- 추천 파라미터 제공
```

주의:

```text
공용으로 재사용하는 것은 모션 파일이 아니라 metadata여야 한다.
```

---

### Phase 5 — Local Provider 실험

목표:

```text
로컬 MDM/MLD/MotionLCM 확장 가능성을 보여준다.
```

구현 방식:

```text
쉬운 버전:
- 미리 생성한 샘플 모션 반환

중간 버전:
- Colab/RunPod에서 생성한 결과를 서버에 저장
- LocalProvider가 그 결과 반환

어려운 버전:
- 서버에서 Python worker 실행
- GPU 추론
- FBX/BVH 변환
```

---

## 14. 최종 추천 방향

### 지금 해야 할 것

```text
1. DeepMotion API 계약부터 하지 않는다.
2. Mock/Manual Provider로 전체 구조를 먼저 만든다.
3. Unreal Editor 안에서 Import / Retarget / Preview / Bake 자동화를 완성한다.
4. 사용자별 private cache만 구현한다.
5. 공용 모션 캐시는 하지 않는다.
6. Metadata 기반 추천 구조만 설계한다.
```

### 나중에 할 것

```text
1. DeepMotion API Access 신청
2. 실제 DeepMotionApiProvider 구현
3. LocalMDMProvider 실험
4. 자체 제작/외주 제작 모션 라이브러리 확보
5. 별도 라이선스 계약 후 공용 캐시 검토
```

---

## 15. 포트폴리오용 소개 문장

```text
본 프로젝트는 Text-to-Motion AI와 Unreal Engine Editor Workflow를 연결하는 AI Motion Pipeline MVP입니다.

사용자는 Unreal Editor 플러그인에서 캐릭터를 선택하고 자연어 프롬프트를 입력합니다.
서버는 프롬프트를 정규화하고 MotionProvider 계층을 통해 DeepMotion 같은 외부 Text-to-Motion API 또는 향후 Local MDM Provider로 요청을 전달합니다.
생성된 FBX/BVH 모션은 서버에 사용자별 private cache로 저장되며, Unreal 플러그인은 이를 자동으로 Import, Retarget, Preview, Bake하여 Animation Sequence로 변환합니다.

초기 MVP는 Mock/Manual Provider를 통해 API 계약 없이 전체 파이프라인을 검증하고,
향후 DeepMotion API, Local MDM, Licensed Motion Library Provider를 교체 가능한 구조로 확장할 수 있도록 설계했습니다.
```

---

## 16. 핵심 결론

```text
- 네가 만들려는 것은 모션 라이브러리가 아니라 모션 생성 파이프라인이다.
- 초기에는 DeepMotion 같은 상용 API가 가장 현실적이다.
- 포트폴리오 단계에서는 실제 API 계약 없이 Manual/Mock Provider로 충분하다.
- 리타겟 품질은 Skeletal Mesh 분석과 UE Retarget 자동화가 핵심이다.
- DeepMotion 결과물을 다른 사용자에게 공용 캐시로 제공하는 것은 라이선스 리스크가 크다.
- 사용자별 private cache는 가능성이 높다.
- 공용 캐시는 나중에 직접 권리를 가진 모션이나 자체 모델 결과물로 해야 한다.
- Local MDM은 가능하지만 UE용 애니메이션 변환 파이프라인 때문에 어렵다.
- 최종 경쟁력은 AI 모델 자체보다 Unreal 개발자가 바로 쓸 수 있는 자동화 워크플로우에 있다.
```
