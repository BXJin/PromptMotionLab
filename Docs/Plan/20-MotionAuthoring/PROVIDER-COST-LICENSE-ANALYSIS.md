# PROVIDER-COST-LICENSE-ANALYSIS — PromptMotionLab

작성일: 2026-05-05

---

## 0. 비용 구조 개요

```text
비용 발생 영역:
1. Text-to-Motion Provider 비용 (핵심)
2. LLM 비용 (prompt normalization)
3. 서버 / 스토리지 / 트래픽 비용
```

핵심 원칙:

```text
비용은 generation에만 발생해야 한다.
Preview와 Bake는 추가 비용이 없어야 한다.

Generate once
→ generated result cache (user private)
→ preview many times
→ bake once
```

---

## 1. Text-to-Motion Provider 비교

### 1.1 상용 서비스 (API 또는 수동 사용)

| Provider | 자동화 API | FBX/BVH export | 포트폴리오 적합성 | 주의 |
|---|---|---|---|---|
| DeepMotion SayMotion | 별도 신청/계약 필요 | 가능 | 높음 | API 접근 신청 절차 있음 |
| Rokoko Text-to-Motion | Studio 기반, API 제한 | 가능 | 중간 | 무료 플랜 제약 있음 |
| Kimodo | 확인 필요 | 확인 필요 | 낮음 | 정보 부족 |
| nocapmocap | 확인 필요 | 확인 필요 | 낮음 | 정보 부족 |
| Rigtix | 확인 필요 | 확인 필요 | 낮음 | 정보 부족 |

### 1.2 오픈소스 (로컬 또는 클라우드 추론)

| 모델 | 라이선스 | 출력 포맷 | UE 연동 난이도 | 주의 |
|---|---|---|---|---|
| MDM | MIT | joint position numpy | 높음 | SMPL→FBX 변환 필요 |
| MotionGPT | MIT | HumanML3D format | 높음 | 변환 파이프라인 필요 |
| MotionDiffuse | MIT | joint sequence | 높음 | 변환 파이프라인 필요 |
| T2M-GPT | MIT | HumanML3D format | 높음 | 변환 파이프라인 필요 |
| MotionLCM | MIT | joint sequence | 높음 | 변환 파이프라인 필요 |

---

## 2. 비용 시나리오

### 옵션 A: 상용 서비스 + 수동 생성 (MVP 권장)

```text
구성:
UE Plugin → FastAPI → ManualMotionProvider (수동 업로드 파일)

비용:
- 모션 생성: 서비스 무료/체험 플랜 내 (DeepMotion 웹 등)
- LLM 정규화: Gemini Flash / GPT-4o-mini → 요청당 $0.001~0.003
- 서버: 로컬 또는 작은 VM → $0~15/월
- Storage: 로컬 폴더 → $0

예상 MVP 총비용:
수동 생성 50회 이내 기준 → $5~30 범위 (LLM 포함)
```

### 옵션 B: 상용 API 자동화

```text
구성:
UE Plugin → FastAPI → CommercialApiProvider → DeepMotion SayMotion API

비용:
- 모션 생성: 서비스 구독 또는 크레딧 (DeepMotion credit 기준 추정 $1~5/generation)
- LLM 정규화: $0.001~0.003/요청
- 서버: VM $5~20/월

예상 월 비용:
포트폴리오 시연 기준 (100회 미만): $20~100
주의: API access 신청 및 승인 필요
```

### 옵션 C: 로컬 PC GPU 추론

```text
구성:
UE Plugin → FastAPI → LocalModelProvider → MDM/MotionGPT (로컬 GPU)

비용:
- 금전 비용: 거의 없음 (전기료 수준)
- 개발 비용: 높음 (SMPL → FBX 변환 파이프라인 필요)
- 위험도: 높음 (품질 불안정, 변환 파이프라인 복잡)

적합한 경우:
ML pipeline 자체를 강하게 어필할 때
```

### 옵션 D: 클라우드 GPU (RunPod / Modal)

```text
구성:
UE Plugin → FastAPI Gateway → Cloud GPU Worker → LocalModelProvider

비용:
- GPU instance: T4 기준 $0.2~0.4/시간
- 필요할 때만 켜는 on-demand 방식 권장
- 시연/촬영 때만 실행

예상 비용:
포트폴리오 시연 기준: $5~30 (가동 시간 한정)
```

### 옵션 E: Colab 수동 생성 (중간 단계)

```text
구성:
Google Colab에서 MDM/MotionGPT 실행
→ 결과 numpy/BVH 생성
→ 변환 스크립트로 BVH 추출
→ 서버 LocalModelProvider 폴더에 업로드
→ UE Plugin이 API처럼 수신

비용:
- Colab Pro: $10~12/월
- 금전 비용은 낮지만 작업이 수동

적합한 경우:
로컬 GPU 없이 오픈소스 모델 결과를 pipeline에 연결할 때
```

---

## 3. LLM 비용 분석

### 역할

```text
1. 사용자 한국어 프롬프트 → 영어 정규화
2. gesture parameter JSON 생성 (Pipeline A)
3. Text-to-Motion 최적화 prompt/constraint 생성 (Pipeline B)
4. Quality report 요약 (선택)
```

### 모델별 비용 추정 (요청당)

| 모델 | 입력 | 출력 | 예상 비용/요청 |
|---|---|---|---|
| GPT-4o-mini | ~200 tokens | ~150 tokens | ~$0.001 |
| Gemini 1.5 Flash | ~200 tokens | ~150 tokens | ~$0.0005 |
| Claude Haiku | ~200 tokens | ~150 tokens | ~$0.001 |
| GPT-4o | ~200 tokens | ~150 tokens | ~$0.005 |

권장: GPT-4o-mini 또는 Gemini 1.5 Flash로 시작.

---

## 4. 라이선스 리스크 분석

### 4.1 안전한 구조: User Private Cache

```text
사용자 A가 프롬프트 요청
→ 서버가 Provider로 생성
→ A의 private cache에 저장
→ A가 같은 프롬프트 재요청 시 기존 결과 반환
→ B에게는 제공하지 않음
```

이 구조는 API 중개 구조상 자연스럽고 라이선스 리스크가 낮다.

### 4.2 위험한 구조: Global Shared Cache

```text
사용자 A가 프롬프트 요청
→ 서버가 DeepMotion API로 생성
→ 서버에 공용 저장
→ 사용자 B도 같은 프롬프트 입력
→ A의 FBX 결과를 B에게 제공
```

이 구조는 DeepMotion 약관에서 "stand-alone asset access" 또는 "asset redistribution"으로 해석될 수 있다. **사용 금지.**

### 4.3 공용으로 재사용해도 상대적으로 안전한 데이터

```text
- 원본 프롬프트 (metadata 목적)
- 정규화된 영어 프롬프트
- gesture tags
- duration
- rootMotion 여부
- skeletonPreset
- quality score
- 성공/실패 로그
- approved 여부
- 생성 모델/버전 정보
```

### 4.4 공용 재사용이 위험한 데이터

```text
- 상용 API로 생성된 FBX
- 상용 API로 생성된 BVH
- 상용 API로 생성된 GLB
- Retarget된 AnimSequence asset
```

### 4.5 라이선스 확보 후 공용 캐시가 가능한 경우

```text
- 직접 제작/외주 제작한 모션
- MIT 라이선스 오픈소스 모델로 생성한 결과 (라이선스 확인 필요)
- 별도 라이선스 계약을 맺은 Provider 결과물
```

---

## 5. 포트폴리오 단계 권장 비용 구조

```text
MVP 단계:
- Manual Provider: 비용 거의 없음
- LLM: $5~10/월 미만
- 서버: 로컬 실행
- 총비용: $0~15/월

Phase 2 (상용 API 연동):
- Provider API: $20~100/월 (사용량 기준)
- LLM: $3~10/월
- 서버 VM: $5~20/월
- 총비용: $30~130/월

Phase 3 (Local Model):
- Colab Pro: $10~12/월
- LLM: $3~10/월
- 서버 VM: $5~20/월
- 총비용: $18~42/월
```

포트폴리오 목적으로는 Phase 1 (Manual Provider) 완성 후 필요한 경우에만 상용 API 연동을 추가하는 것이 비용 대비 효율적이다.
