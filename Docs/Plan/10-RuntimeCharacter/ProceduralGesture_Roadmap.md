# Procedural Gesture 확장 로드맵

---

## 캐릭터 선택지 비교: MetaHuman vs CC4 (Character Creator 4)

### CC4란?
**Character Creator 4 (CC4)** 는 Reallusion사의 3D 캐릭터 제작 툴로 만든 캐릭터 포맷이다.
- FBX 기반 → UE5, Unity, Blender 등 범용 이식 가능
- `cc_base_` prefix의 bone 명명 규칙이 특징
- 현재 `child_test_2`(`unreal_file`) 가 CC4 기반으로 확인됨 (bone prefix로 판별)

### MetaHuman vs CC4 비교표

| 항목 | MetaHuman | CC4 (child_test_2) |
|------|-----------|-------------------|
| **얼굴 bone 수** | ~500개+ (개별 lip/cheek/brow bone) | 14개 (jaw, eye×2, tongue×3, teeth 등) |
| **눈 bone** | ✅ 있음 | ✅ `cc_base_l/r_eye` |
| **턱 bone** | ✅ 있음 | ✅ `cc_base_jawroot` |
| **눈썹/볼/입술 bone** | ✅ 개별 bone | ❌ → morph target으로 대체 |
| **ARKit 52 blendshape** | ✅ 표준 이름 매핑 | △ 유사하나 이름 비표준 |
| **Morph target 수** | ~400+ | 265개 (확인됨) |
| **Facial curve driver** | Control Rig 기반 | 319개 커브 (Maya/DAZ 방식) |
| **플랫폼 이식성** | Unreal 전용 | FBX → 범용 |
| **퍼포먼스 무게** | 무거움 (고사양 GPU 권장) | 상대적으로 가벼움 |
| **커스터마이징** | 제한적 (Groom, 고정 구조) | 자유로움 (CC4 앱에서 편집) |
| **모바일 적합성** | MetaHuman Mobile LOD 필요 (UE 5.3+) | 상대적으로 유리 |
| **라이선스** | Unreal Engine 종속 | FBX 기반 자유 배포 가능 |

### MVP 목표 달성 가능성

| 기능 | MetaHuman | CC4 |
|------|-----------|-----|
| 눈 깜빡임 | bone + morph | morph target |
| 시선 이동 | 눈 bone 회전 | `cc_base_l/r_eye` bone 회전 ✅ |
| 고개 끄덕임 | `head` bone | `head` bone ✅ |
| 입모양/립싱크 | ARKit jaw + 립 bone | `cc_base_jawroot` + `V_` viseme morph ✅ |
| 눈썹/볼 표정 | 개별 bone 정밀 제어 | morph target blend (정밀도 낮음) |
| 고민/기쁨 표정 | bone + morph | morph target 265개 ✅ |

**결론**: MVP 수준(눈 깜빡임·시선·고개·표정·립싱크)은 CC4로 충분히 달성 가능.
눈썹/볼 등 세밀한 bone 제어가 필요하면 MetaHuman이 유리.

---

## 캐릭터 내부 구조 확인 방법 (UE Python)

### 1. 전체 bone 목록 확인

```python
import unreal

mesh = unreal.load_asset('/Game/child_test_2/mesh/unreal_file')
skel = mesh.get_editor_property('skeleton')
ref_pose = skel.get_reference_pose()
bone_names = unreal.AnimPoseExtensions.get_bone_names(ref_pose)
print(f"총 bone 수: {len(bone_names)}")
for b in sorted([str(b) for b in bone_names]):
    print(b)
```

### 2. 얼굴 관련 bone 필터링

```python
face_kw = ['head','neck','jaw','eye','tongue','teeth','lip','ear','chin','face','brow','nose']
face_bones = sorted([str(b) for b in bone_names if any(k in str(b).lower() for k in face_kw)])
print(f"얼굴 bone: {face_bones}")
```

**child_test_2 결과 (확인 완료):**
```
cc_base_facialbone, cc_base_jawroot, cc_base_l_eye, cc_base_r_eye,
cc_base_teeth01, cc_base_teeth02, cc_base_tongue01/02/03,
cc_base_upperjaw, head, neck_01
```

### 3. Morph Target 목록 확인

```python
mesh = unreal.load_asset('/Game/child_test_2/mesh/unreal_file')
morph_names = mesh.get_editor_property('morphTargets')
print(f"Morph target 수: {len(morph_names)}")
for m in morph_names:
    print(m.get_name())
```

**child_test_2 결과**: 265개 확인됨 (ARKit 유사 + `V_` viseme 립싱크 포함)

### 4. Facial Curve Driver (Skeleton curve) 목록 확인

```python
skel = mesh.get_editor_property('skeleton')
curve_names = skel.get_curve_meta_data_names()
print(f"커브 수: {len(curve_names)}")
for c in curve_names:
    print(c)
```

**child_test_2 결과**: 319개 확인됨
- `blendOrient1`, `blendParent1` 등 Maya/DAZ 방식 드라이버 커브
- `V_Tongue_up`, `DistanceToApex` 등 아티큘레이션 제어 커브

### 5. Control Rig의 Control 목록 확인

```python
cr = unreal.load_asset('/Game/Animation/ControlRig/CR_Mannequin_Body')
hierarchy = cr.get_editor_property('hierarchy')  # RigHierarchy
controls = hierarchy.get_all_controls()
for c in controls:
    print(c.get_name())
```

> **주의**: `CR_Mannequin_Procedural`은 control이 0개 (correction curve 전용).
> Gesture 제어는 반드시 `CR_Mannequin_Body` 사용.

---

## 최종 목표

Procedural JSON 기반으로 `child_test_2` (커스텀 캐릭터) 에서  
**얼굴 표정 + 손 흔들기 등 간단한 gesture**를 Control Rig로 실시간 조작.

---

## 현재 상태 (2026-05)

| 항목 | 값 |
|------|-----|
| **테스트 BP** | `BP_ThirdPersonCharacter_CRTest` — mesh=SKM_Manny, AnimClass=ABP_Quinn |
| **최종 대상 BP** | `BP_ThirdPersonCharacter` — mesh=unreal_file (UE4 skeleton) |
| **제어 rig** | `CR_Mannequin_Body` (FK/IK 컨트롤 148개) |
| **사용 불가 rig** | `CR_Mannequin_Procedural` — 보정 커브 전용, 직접 gesture 제어 불가 |
| **unreal_file skeleton** | `/Game/Characters/Mannequin_UE4/Meshes/SK_Mannequin_Skeleton` (UE4) |
| **SKM_Manny skeleton** | `/Game/Characters/Mannequins/Meshes/SK_Mannequin` (UE5) |

> **CR_Mannequin_Procedural는 joint correction curve 전용 rig** (MoveData_Speed, calf_l_back_50 등).  
> Gesture 제어는 **CR_Mannequin_Body**의 FK/IK control을 사용해야 한다.

---

## Rig 선택 근거

| Rig | 구성 | 용도 |
|-----|------|------|
| `CR_Mannequin_Procedural` | Curve 109개, Control 0개 | 포즈 보정 자동화 (내부용) |
| `CR_Mannequin_Body` | Control 148개, Bone 346개 | FK/IK 직접 조작 → **gesture 제어 대상** |
| `CR_Mannequin_BasicFootIK` | - | 발 IK 전용 |

---

## Procedural JSON → CR_Mannequin_Body Control 매핑 (확정)

### 상체 gesture (손 흔들기, 고개 끄덕 등)

| Procedural JSON field | CR_Mannequin_Body control | 비고 |
|----------------------|--------------------------|------|
| `shoulderRaise_l` | `clavicle_l_ctrl` | 어깨 올리기 |
| `shoulderRaise_r` | `clavicle_r_ctrl` | |
| `elbowBend_l` | `lowerarm_l_fk_ctrl` | 팔꿈치 굽히기 (FK 모드) |
| `elbowBend_r` | `lowerarm_r_fk_ctrl` | |
| `wristWave_l` | `hand_l_fk_ctrl` | 손 흔들기 (FK 모드) |
| `wristWave_r` | `hand_r_fk_ctrl` | |
| `handIK_l` | `hand_l_ik_ctrl` | 손 위치 직접 지정 (IK 모드) |
| `handIK_r` | `hand_r_ik_ctrl` | |
| `bodyLean` | `body_offset_ctrl` | 몸통 기울기 |
| `chestTwist` | `chest_ctrl` | 가슴 회전 |
| `spineBend` | `spine_03_ctrl` | 허리 굽히기 |
| `headNod` | `head_ctrl` | 고개 끄덕 |
| `headIK` | `head_ik_ctrl` | 고개 IK 위치 |
| `neckTilt` | `neck_01_ctrl` | 목 기울기 |

### 손가락 curl (주먹/펼치기)

| Procedural JSON field | L control | R control |
|----------------------|-----------|-----------|
| `thumbCurl` | `thumb_curl_l_ctrl` | `thumb_curl_r_ctrl` |
| `indexCurl` | `index_curl_l_ctrl` | `index_curl_r_ctrl` |
| `middleCurl` | `middle_curl_l_ctrl` | `middle_curl_r_ctrl` |
| `ringCurl` | `ring_curl_l_ctrl` | `ring_curl_r_ctrl` |
| `pinkyCurl` | `pinky_curl_l_ctrl` | `pinky_curl_r_ctrl` |

### FK / IK 스위치

| control | 기능 |
|---------|------|
| `arm_l_fk_ik_switch` | 왼팔 FK↔IK 전환 |
| `arm_r_fk_ik_switch` | 오른팔 FK↔IK 전환 |
| `spine_fk_ik_switch` | 척추 FK↔IK 전환 |
| `neck_fk_ik_switch` | 목 FK↔IK 전환 |

---

## 파이프라인 구조

```
Procedural JSON
      ↓
PromptMotionEditor
  - SkeletonPreset 판별 (Skeleton path 기반)
  - JSON field → CR control name 변환 (매핑 테이블)
      ↓
CR_Mannequin_Body
  - SetControlRotation / SetControlTransform
      ↓
AnimBlueprint (ABP_Quinn)
      ↓
SkeletalMesh (현재: SKM_Manny → 목표: unreal_file)
```

---

## Phase 1 — Manny 기준 CR 파이프라인 검증 (현재 단계)

**사용 Asset:** `BP_ThirdPersonCharacter_CRTest` (SKM_Manny + ABP_Quinn)

**검증 gesture (쉬운 것부터):**

1. `wristWave_r` → `hand_r_fk_ctrl` rotation 변경 → 손 흔들기
2. `headNod` → `head_ctrl` rotation pitch
3. `shoulderRaise_r` → `clavicle_r_ctrl` rotation
4. `bodyLean` → `body_offset_ctrl` rotation

**완료 기준:**
- 런타임에서 `SetControlRotation` 호출 시 캐릭터가 반응하는 것 확인
- JSON field → control name 매핑이 실제로 동작함을 검증

---

## Phase 2 — child_test_2 (unreal_file) 확장

Skeleton 불일치 해결 경로:

### 경로 A: IK Retargeter (비파괴적, 권장)

```
CR_Mannequin_Body (UE5 SK_Mannequin)
      ↓  IK Retargeter
unreal_file AnimBP (UE4 SK_Mannequin_Skeleton)
      ↓
unreal_file mesh
```

작업: IK Rig × 2 생성 → IK Retargeter 연결 → unreal_file 전용 AnimBP 생성

### 경로 B: Skeleton 교체 (근본 해결)

`unreal_file` FBX를 UE5 SK_Mannequin 기준으로 재임포트.  
이후 ABP_Quinn + CR_Mannequin_Body 직접 사용 가능.

---

## Phase 3 — 얼굴 Procedural Gesture

`unreal_file` 재질 슬롯 기준 (Std_Eye, Std_Tongue, Std_Skin 등) → MetaHuman/DAZ 계열 구조 예상.

### 방식 A: Morph Target 직접 제어 (우선 시도)

```
Procedural JSON (expression: "smile", value: 0.8)
      ↓
SkeletalMeshComponent.SetMorphTarget("smile", 0.8)
```

**선행 확인 필요:**
```python
mesh = unreal.load_asset('/Game/child_test_2/mesh/unreal_file')
# morph target 목록 확인
```

### 방식 B: Facial Control Rig (고급)

별도 Facial CR asset이 있을 경우 Body CR과 레이어 분리하여 구성.

---

## PromptMotionEditor 수정 포인트

### SkeletonPreset 판별 로직

```
mesh.Skeleton.path == ".../Mannequins/Meshes/SK_Mannequin"
  → preset: ue5_manny  →  CR_Mannequin_Body 사용

mesh.Skeleton.path == ".../Mannequin_UE4/Meshes/SK_Mannequin_Skeleton"
  → preset: ue4_mannequin  →  IK Retargeter 경유 or 별도 CR

그 외
  → preset: unknown
```

### 향후 DataAsset 기반 확장 구조 (예시)

```
DA_SkeletonPreset_UE5Manny
  skeletonPath: ".../SK_Mannequin"
  controlRigAsset: CR_Mannequin_Body
  gestureMapping: { wristWave_r: "hand_r_fk_ctrl", ... }

DA_SkeletonPreset_UE4Mannequin
  skeletonPath: ".../SK_Mannequin_Skeleton"
  controlRigAsset: CR_Mannequin_Body (via Retargeter)
  gestureMapping: { ... }
```

---

## 작업 순서

```
[지금]   Phase 1: CRTest에서 CR_Mannequin_Body SetControlRotation 동작 검증
                   wristWave → hand_r_fk_ctrl 부터 시작

[다음]   Phase 2: unreal_file Skeleton 처리
                   경로 A (IK Retargeter) 권장

[이후]   Phase 3: unreal_file Morph Target 목록 확인 → 얼굴 gesture 구현
```
