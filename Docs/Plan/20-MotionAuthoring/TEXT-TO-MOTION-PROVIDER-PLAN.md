# TEXT-TO-MOTION-PROVIDER-PLAN — PromptMotionLab

작성일: 2026-05-05

---

## 0. 목적

이 문서는 Pipeline B (Text-to-Motion Provider 기반 모션 생성) 에서 사용할 Provider의 선택 기준, 연동 방식, 단계별 적용 전략을 정리한다.

---

## 1. Provider 추상화 구조

```python
class IMotionProvider(ABC):
    @abstractmethod
    async def generate(self, request: MotionRequest) -> MotionResult:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def get_output_formats(self) -> list[str]:
        pass
```

### Provider 구현체 목록

```text
ManualMotionProvider
ProceduralJsonProvider
DeepMotionManualProvider
DeepMotionApiProvider
RokokoManualProvider
ColabLocalModelProvider
LocalModelProvider (GPU direct)
UserPrivateCacheProvider
```

---

## 2. MVP 1차: ManualMotionProvider

### 개념

```text
외부 툴(DeepMotion 웹, Rokoko Studio 등)에서 수동으로 생성한
FBX / BVH 파일을 서버 폴더에 업로드하고,
UE Plugin이 API 결과처럼 수신해 전체 pipeline을 검증한다.
```

### 구현

```text
서버 폴더 구조:
/storage/manual/
├── wave_friendly_manny.fbx
├── bow_calm_manny.bvh
├── explain_point_manny.fbx
└── manual_registry.json

manual_registry.json:
{
  "entries": [
    {
      "promptKeyword": "wave friendly",
      "skeletonPreset": "Manny",
      "filePath": "wave_friendly_manny.fbx",
      "format": "fbx",
      "duration": 1.8,
      "rootMotion": false
    }
  ]
}
```

### 요청 흐름

```text
Plugin → POST /api/generate/motion { prompt: "손 흔들어줘", skeletonPreset: "Manny", provider: "manual" }
Server → prompt keyword 매핑 → manual_registry.json에서 파일 찾기
Server → Job ID 발급 (즉시 completed)
Plugin → GET /api/job/{id}/result → FBX binary 다운로드
Plugin → Import / Retarget / Preview / Bake
```

### 장점

```text
- API 비용 없음
- 전체 pipeline 검증 가능
- 포트폴리오 시연에 완전히 충분
- 구현 난이도 낮음
```

---

## 3. MVP 2차: DeepMotionManualProvider

### 개념

```text
DeepMotion SayMotion 웹에서 수동으로 생성한 결과를
서버에 업로드하고 ManualMotionProvider처럼 서빙한다.
단, 파일 출처를 "DeepMotion SayMotion 생성 결과"로 명시한다.
```

### 작업 흐름

```text
1. DeepMotion SayMotion 웹 접속
2. Prompt 입력: "A friendly standing character waves hello with the right hand. Upper body, feet planted."
3. 생성 결과 확인
4. FBX / BVH / GLB 다운로드
5. 서버 /storage/deepmotion_manual/ 폴더에 업로드
6. deepmotion_registry.json 업데이트
7. UE Plugin에서 해당 prompt로 요청 시 파일 반환
```

### 라이선스 주의

```text
DeepMotion 생성 결과물은 사용자 개인 사용 목적으로만 서빙한다.
다른 사용자에게 동일 파일을 공유하지 않는다. (Private Cache 원칙)
```

---

## 4. Phase 3: CommercialApiProvider (DeepMotion API)

### 필요 조건

```text
- DeepMotion API Access 신청 및 승인
- Client ID / Client Secret 발급
- SayMotion API endpoint 확인
```

### 예상 API 호출 흐름

```text
POST https://api.deepmotion.com/v1/saymotion/generate
Headers: Authorization: Bearer {access_token}
Body:
{
  "prompt": "A friendly character waves hello with right hand. Upper body gesture, feet planted.",
  "duration": 2.0,
  "fps": 30,
  "format": "fbx"
}

Response (async):
{
  "jobId": "dm_abc123",
  "status": "processing",
  "estimatedTime": 10
}

GET https://api.deepmotion.com/v1/jobs/dm_abc123
→ { "status": "completed", "downloadUrl": "https://..." }
```

### 서버 Provider 구현

```python
class DeepMotionApiProvider(IMotionProvider):
    async def generate(self, request: MotionRequest) -> MotionResult:
        # 1. LLM으로 prompt normalization
        normalized = await self.normalize_prompt(request.prompt)
        # 2. DeepMotion API 호출
        job_id = await self.call_deepmotion_api(normalized)
        # 3. 결과 폴링
        result_url = await self.poll_until_completed(job_id)
        # 4. FBX 다운로드 및 로컬 저장
        local_path = await self.download_result(result_url)
        # 5. User private cache에 저장
        await self.cache_result(request.user_id, request.prompt_hash, local_path)
        return MotionResult(file_path=local_path, format="fbx")
```

---

## 5. Phase 4: ColabLocalModelProvider (오픈소스 모델)

### 개념

```text
Google Colab 또는 RunPod에서 MDM / MotionGPT 등 오픈소스 모델을 실행하고
생성 결과(BVH 또는 numpy)를 변환 스크립트로 BVH로 추출한 뒤
서버에 업로드해 LocalModelProvider로 서빙한다.
```

### 작업 흐름

```text
1. Colab에서 MDM 또는 MotionGPT 실행
2. Prompt 입력
3. joint position sequence (numpy) 생성
4. SMPL / HumanML3D → BVH 변환 스크립트 실행
5. 결과 BVH 다운로드
6. 서버 /storage/local_model/ 폴더에 업로드
7. UE Plugin에서 BVH Import / Retarget
```

### 오픈소스 모델 → UE 변환 파이프라인 (어려운 부분)

```text
모델 출력:
- joint position array (numpy): shape (frames, joints, 3)
- SMPL pose parameters
- HumanML3D motion representation

UE가 원하는 것:
- BVH (bone hierarchy + frame별 rotation)
- FBX Animation
- UE Skeleton 기준 Animation Sequence

변환 과정:
1. joint position → bone rotation 계산 (FK inverse 또는 IK)
2. SMPL joint mapping → standard humanoid joint 이름
3. BVH hierarchy 생성
4. root motion 계산
5. BVH export
6. UE Import → Retarget → Preview
```

### 변환 도구 후보

```text
- blendermotion (Blender + Python)
- smplx_to_bvh
- HumanML3D 공식 visualization 코드 수정
- custom Python 변환 스크립트
```

### 주의

```text
이 단계는 난이도가 높다.
변환 품질 문제(foot sliding, root drift, rotation discontinuity)가 자주 발생한다.
포트폴리오 목적이라면 Colab 수동 생성 + 결과 파일 업로드 방식으로 단계를 낮추는 것이 현실적이다.
```

---

## 6. 오픈소스 모델 정리

| 모델 | 라이선스 | 출력 | 품질 | 변환 난이도 |
|---|---|---|---|---|
| MDM | MIT | joint position numpy | 중간 | 높음 |
| MotionGPT | MIT | HumanML3D format | 중간 | 높음 |
| MotionDiffuse | MIT | joint sequence | 중간 | 높음 |
| T2M-GPT | MIT | HumanML3D format | 중간 | 높음 |
| MotionLCM | MIT | joint sequence | 중간 | 높음 |

모두 공통적으로:

```text
- GPU 필요 (최소 RTX 3060 수준 또는 Colab T4)
- SMPL / HumanML3D → BVH 변환이 필요
- UE Skeleton 매핑 작업이 추가로 필요
- 상용 API 대비 품질 편차가 크고 불안정
```

---

## 7. Provider 단계별 전략

```text
Phase 1 (지금):
- ManualMotionProvider
- 수동 생성 FBX/BVH 파일 사용
- 전체 UE Pipeline 완성

Phase 2 (다음):
- DeepMotionManualProvider
- DeepMotion 웹에서 생성 + 서버에 등록
- 실제 상용 T2M 결과를 pipeline에 연결

Phase 3 (선택):
- DeepMotionApiProvider
- API Access 확보 시 자동 생성 연결

Phase 4 (선택):
- ColabLocalModelProvider
- 오픈소스 모델 결과를 BVH 변환 후 서빙

Phase 5 (고급):
- LocalModelProvider with GPU inference
- Python Worker에서 직접 모델 실행
```

---

## 8. Motion Format 전략

### Preview용

```text
JSON bone transform sequence (권장)
- 서버와 Plugin 간 내부 포맷
- 파일 크기 작음
- 직접 Control Rig 또는 PoseableMesh에 적용 가능

BVH
- 비교적 작고 표준화된 포맷
- Blender/Maya에서도 검증 가능
- UE Import 가능
```

### 최종 저장용

```text
UE AnimSequence (bake 결과)
- 이후 runtime에서 일반 UE animation처럼 사용
- Montage, State Machine, BlendSpace 연결 가능
```

### 외부 연동용

```text
FBX Animation
- 상용 툴 결과물의 표준 포맷
- UE Import / Retarget 지원

GLB Animation
- 경량화 포맷
- UE 5.1+ Import 가능 (glTF 지원)
```

---

## 9. UE에서 motion result 적용 흐름 (상세)

```text
1. Plugin이 FBX binary 수신 (HTTP response)
2. /Game/PromptMotionLab/Generated/ 폴더에 임시 저장
3. FbxImportHelper로 FBX Import
   - skeleton: source skeleton (FBX 내 skeleton)
   - import type: Animation only (mesh 제외)
4. IK Retargeter로 retarget
   - source: FBX skeleton (Mixamo / DeepMotion humanoid)
   - target: 선택된 캐릭터 Skeleton (Manny 등)
5. Preview Actor에 retarget 결과 적용
6. Quality Validator 실행
7. 사용자 Approve / Reject
8. Approve 시:
   - /Game/PromptMotionLab/Approved/ 폴더에 복사
   - AnimSequence로 bake (선택 시)
9. Reject 시:
   - 임시 파일 삭제
   - 재생성 또는 Pipeline A로 전환
```
