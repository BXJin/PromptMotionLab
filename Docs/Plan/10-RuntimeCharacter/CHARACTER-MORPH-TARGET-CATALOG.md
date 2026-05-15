# Character Morph Target Catalog

Updated: 2026-05-15
Source: UE Editor Python query via `get_all_morph_target_names()`

---

## 캐릭터 에셋 정보

| 항목 | child_test_2 | child_female_test1 |
|---|---|---|
| UE 에셋 경로 | `/Game/child_test_2/mesh/unreal_file` | `/Game/chlid_femele_test1/mesh/unreal_file` |
| **폴더명 오타** | 없음 | `chlid_femele` (child_female 오타) |
| 총 morph target 수 | **265개** | **279개** |
| 공통 morph 수 | 265개 | 265개 (동일 세트 포함) |
| 추가 morph | 없음 | 14개 (hair + body scale 계열) |

> **크기 차이 원인**: child_female_test1에만 `Scale`, `Scale Forehead`, `Scale Top`, `Side Scale`, `Side Up` 등 body shape morph가 존재한다. 이 morph들이 CC4에서 캐릭터 슬라이더 값으로 non-zero 상태로 bake된 경우 메시 형태가 달라진다. 단, UE 씬 내 물리적 크기 차이는 **FBX import scale 차이** 또는 **CC4에서 설계된 신장 자체 차이**일 가능성이 높다. Physics Asset은 시각적 크기에 영향을 주지 않으며, 크기 불일치로 physics capsule이 메시보다 크게 보이는 것은 Physics Asset을 해당 캐릭터 기준으로 regenerate하지 않아서 발생한 것이다.

---

## Morph 카테고리 분류

### 1. Expression Layer — Behavior JSON에서 직접 제어

표정 preset과 감정 intensity 기반으로 Unreal이 blend하는 주요 morph.

#### 1-1. Brow (눈썹)

| Morph | 설명 | 주요 Preset 활용 |
|---|---|---|
| `Brow_Compress_L/R` | 눈썹 가운데로 모임 | Angry, Concerned, Confused |
| `Brow_Drop_L/R` | 눈썹 아래로 내려감 | Sad, Serious, Angry |
| `Brow_Raise_Inner_L/R` | 눈썹 안쪽 올라감 | Worried, Sad, Surprised |
| `Brow_Raise_Outer_L/R` | 눈썹 바깥쪽 올라감 | Surprised, Happy, Curious |

#### 1-2. Cheek (볼)

| Morph | 설명 | 주요 Preset 활용 |
|---|---|---|
| `Cheek_Puff_L/R` | 볼 부풀림 | (특수 표정) |
| `Cheek_Raise_L/R` | 볼 올라감 (웃을 때 자연스럽게) | Smile, Happy, Laugh |
| `Cheek_Suck_L/R` | 볼 안으로 당김 | Thinking, Uncertain |

#### 1-3. Eye (눈 - 표정 계열)

| Morph | 설명 | 주요 Preset 활용 |
|---|---|---|
| `Eye_Blink_L/R` | 눈 깜빡임 | Idle layer (자동) |
| `Eye_Squint_L/R` | 눈 가늘게 뜸 | Smile, Suspicious, Thinking |
| `Eye_Wide_L/R` | 눈 크게 뜸 | Surprised, Curious, Alert |
| `Eye_Pupil_Contract` | 동공 수축 | (조명 반응, 선택적) |
| `Eye_Pupil_Dilate` | 동공 확장 | (감정 반응, 선택적) |

#### 1-4. Nose (코)

| Morph | 설명 | 주요 Preset 활용 |
|---|---|---|
| `Nose_Crease_L/R` | 코 옆 주름 | Laugh, Happy |
| `Nose_Sneer_L/R` | 코 찡그림 | Disgusted, Angry |
| `Nose_Nostril_Dilate_L/R` | 콧구멍 확장 | Breathing heavy (선택적) |
| `Nose_Nostril_Down/Raise_L/R` | 콧구멍 아래/위 | (미세 조정) |
| `Nose_Tip_Down/Up/L/R` | 코끝 방향 | (미세 조정) |

#### 1-5. Mouth — Expression (입 - 표정 계열)

> ⚠️ 아래 mouth morph는 **Expression layer** 담당. Jaw_Open / Mouth_Close / V_ 계열과 layer 충돌에 주의.

| Morph | 설명 | 주요 Preset 활용 |
|---|---|---|
| `Mouth_Smile_L/R` | 입꼬리 올라감 | Smile, Happy, Friendly |
| `Mouth_Smile_Sharp_L/R` | 입꼬리 강하게 올라감 | Laugh, Very Happy |
| `Mouth_Frown_L/R` | 입꼬리 내려감 | Sad, Concerned, Apologetic |
| `Mouth_Dimple_L/R` | 보조개 | Smile 보조 |
| `Mouth_Stretch_L/R` | 입 양옆으로 당김 | Nervous, Awkward Smile |
| `Mouth_Tighten_L/R` | 입술 조임 | Thinking, Hesitant |
| `Mouth_Press_L/R` | 입술 눌림 | Thinking, Determined |
| `Mouth_Chin_Up` | 턱 올라감 | Proud, Confident |
| `Mouth_Down/Up` | 입 전체 아래/위 | 포즈 조정 |
| `Mouth_Contract` | 입 모아짐 | Concerned |
| `Mouth_Shrug_Lower/Upper` | 입술 으쓱 | Uncertain, Shrug |

---

### 2. Gaze Layer — Eye Look Direction

Behavior JSON의 `gazeTarget`에 따라 Unreal GazeAdapter가 제어.

| Morph | 설명 |
|---|---|
| `Eye_L_Look_Down` | 왼쪽 눈 아래 시선 |
| `Eye_L_Look_Up` | 왼쪽 눈 위 시선 |
| `Eye_L_Look_L` | 왼쪽 눈 왼쪽 시선 |
| `Eye_L_Look_R` | 왼쪽 눈 오른쪽 시선 |
| `Eye_R_Look_Down` | 오른쪽 눈 아래 시선 |
| `Eye_R_Look_Up` | 오른쪽 눈 위 시선 |
| `Eye_R_Look_L` | 오른쪽 눈 왼쪽 시선 |
| `Eye_R_Look_R` | 오른쪽 눈 오른쪽 시선 |

> bone 기반 eye control과 병행 검토 필요. morph-based gaze는 micro movement에 보조로 쓸 수 있음.

---

### 3. Head Motion Layer

Behavior JSON의 `headMotion` 키에 따라 적용.

| Morph | 설명 | Behavior JSON 매핑 |
|---|---|---|
| `Head_Turn_L/R` | 고개 좌우 회전 | `gaze: "left"/"right"` |
| `Head_Turn_Down/Up` | 고개 위아래 회전 | `gaze: "down"/"up"` |
| `Head_Tilt_L/R` | 고개 기울임 | `headMotion: "tilt"` |
| `Head_Forward` | 고개 앞으로 | `headMotion: "nod_forward"` |
| `Head_Backward` | 고개 뒤로 | `headMotion: "lean_back"` |
| `Head_L/R` | 고개 좌우 이동 | (선택적) |

> ⚠️ bone-based head rotation과 morph-based head rotation을 동시에 쓰면 충돌 가능. MVP에서는 bone rotation 우선, morph는 보조.

---

### 4. LipSync Layer — V_ Viseme

Azure TTS viseme event → CC4 V_ morph 매핑. **Expression layer와 분리 필수.**

| Morph | 설명 | Azure Viseme ID (참고) |
|---|---|---|
| `V_Open` | 입 크게 열림 | ah, aa 계열 |
| `V_Lip_Open` | 입술 벌어짐 | 일반 모음 |
| `V_Wide` | 입 넓게 벌어짐 | ae, eh 계열 |
| `V_Tight` | 입술 좁아짐 | oo, uw 계열 |
| `V_Tight_O` | 입술 둥글게 좁아짐 | oh, ow 계열 |
| `V_Dental_Lip` | 윗니-아랫입술 접촉 | f, v 계열 |
| `V_Affricate` | 파찰음 | ch, j 계열 |
| `V_Explosive` | 파열음 | p, b, t, d, k, g |
| `V_Tongue_Out` | 혀 앞으로 | th 계열 |
| `V_Tongue_Raise` | 혀 올라감 | l, n 계열 |
| `V_Tongue_up` | 혀 위로 | (r 계열) |
| `V_Tongue_Lower` | 혀 내려감 | (보조) |
| `V_Tongue_Narrow` | 혀 좁아짐 | s, z 계열 |
| `V_Tongue_Curl_D/U` | 혀 아래/위로 말림 | (보조) |

#### Layer 충돌 규칙

```
Jaw_Open, Mouth_Close → LipSync layer가 우선 제어
Mouth_Smile_L/R       → Expression layer가 유지하되 LipSync가 Jaw_Open 시 weight 제한
V_* morphs            → LipSync layer 전담
```

---

### 5. Jaw Layer

LipSync와 Expression layer 사이에 위치. 우선순위는 LipSync > Jaw > Expression.

| Morph | 설명 |
|---|---|
| `Jaw_Open` | 턱 열림 (가장 중요) |
| `Jaw_Down` | 턱 아래로 |
| `Jaw_Forward/Backward` | 턱 앞뒤 |
| `Jaw_L/R` | 턱 좌우 |
| `Jaw_Up` | 턱 위로 (닫힘 보조) |
| `Mouth_Close` | 입술 닫힘 |
| `Mouth_Blow_L/R` | 볼 바람 넣기 |

---

### 6. EO (Eye Orbit) — 눈 소켓 모양 (34개)

MVP에서는 직접 제어하지 않고 expression preset 내부에 포함시킨다.

```
EO Bulge L/R
EO Center Lower/Upper Depth/Height L/R
EO Depth L/R
EO Duct Depth L/R
EO Inner/Outer Depth/Height/Width L/R
EO Inner/Outer Lower/Upper Depth/Height L/R
EO Lower/Upper Depth L/R
```

---

### 7. TL (Lower Eyelid) — 아래 눈꺼풀 (34개)

MVP에서는 직접 제어하지 않고 expression preset 내부에 포함시킨다.

```
TL Center Lower/Upper Depth/Height L/R
TL Depth L/R
TL Duct Depth L/R
TL Inner/Outer Depth/Height/Width L/R
TL Inner/Outer Lower/Upper Depth/Height L/R
TL Lower/Upper Depth L/R
```

---

### 8. Tongue (혀) — LipSync 보조

V_ morph로 커버되지 않는 혀 모양 세밀 제어. MVP에서는 V_ morph 우선, Tongue는 후순위.

```
Tongue_Bulge_L/R, Tongue_Down, Tongue_Enlarge, Tongue_Extend
Tongue_In, Tongue_L/R, Tongue_Mid_Up, Tongue_Narrow
Tongue_Out, Tongue_Roll, Tongue_Tip_Down/Up/L/R
Tongue_Twist_L/R, Tongue_Up, Tongue_Wide
```

---

### 9. Neck (목)

표정 preset에 보조로 포함 가능.

| Morph | 설명 |
|---|---|
| `Neck_Swallow_Down/Up` | 목 삼키는 동작 |
| `Neck_Tighten_L/R` | 목 근육 긴장 |

---

### 10. Eyelash (속눈썹)

Expression preset 내부에 포함. 직접 제어 안 함.

```
Eyelash_Lower_Down/Up_L/R
Eyelash_Upper_Down/Up_L/R
```

---

### 11. Ear (귀) — 거의 사용 안 함

```
Ear_Down_L/R, Ear_Out_L/R, Ear_Up_L/R
```

---

### 12. child_female_test1 전용 Morph (14개)

child_test_2에는 없고 child_female_test1에만 있음.

| Morph | 분류 | 설명 |
|---|---|---|
| `Scale` | Body Scale | 전체 체형 크기 (CC4 슬라이더) |
| `Scale Forehead` | Body Scale | 이마 크기 |
| `Scale Top` | Body Scale | 머리 위 크기 |
| `Side Scale` | Body Scale | 측면 크기 |
| `Side Up` | Body Scale | 측면 높이 |
| `Above Ear` | Hair Shape | 귀 위 머리카락 |
| `Back Length` | Hair Shape | 뒷머리 길이 |
| `Back Scale` | Hair Shape | 뒷머리 크기 |
| `Back Width` | Hair Shape | 뒷머리 너비 |
| `Forehead L/M/R` | Head Shape | 이마 좌/중/우 |
| `Forehead Peak` | Head Shape | 이마 정수리 |
| `Forehead Up` | Head Shape | 이마 위 |

> Body Scale morphs (`Scale`, `Scale Forehead` 등)는 CC4에서 캐릭터 체형 조절 시 bake된 값. **이 morph들이 non-zero이면 캐릭터 외형이 달라 보인다.** 크기 차이 원인 후보.

---

## Facial Expression Preset 설계안

MVP에서는 LLM이 preset 이름 + intensity만 고르고, Unreal이 이 표에서 morph 값을 읽어 blend한다.

```json
{
  "Neutral": {
    "Brow_Raise_Inner_L": 0.0, "Brow_Raise_Inner_R": 0.0,
    "Brow_Compress_L": 0.0, "Brow_Compress_R": 0.0,
    "Eye_Squint_L": 0.0, "Eye_Squint_R": 0.0,
    "Eye_Wide_L": 0.0, "Eye_Wide_R": 0.0,
    "Mouth_Smile_L": 0.0, "Mouth_Smile_R": 0.0,
    "Mouth_Frown_L": 0.0, "Mouth_Frown_R": 0.0,
    "Cheek_Raise_L": 0.0, "Cheek_Raise_R": 0.0
  },
  "Smile": {
    "Mouth_Smile_L": 0.6, "Mouth_Smile_R": 0.6,
    "Cheek_Raise_L": 0.4, "Cheek_Raise_R": 0.4,
    "Eye_Squint_L": 0.2, "Eye_Squint_R": 0.2,
    "Nose_Crease_L": 0.15, "Nose_Crease_R": 0.15
  },
  "Thinking": {
    "Brow_Raise_Inner_L": 0.3, "Brow_Raise_Inner_R": 0.3,
    "Brow_Compress_L": 0.15, "Brow_Compress_R": 0.15,
    "Eye_Squint_L": 0.1, "Eye_Squint_R": 0.1,
    "Mouth_Tighten_L": 0.2, "Mouth_Tighten_R": 0.2,
    "Mouth_Press_L": 0.15, "Mouth_Press_R": 0.15
  },
  "Surprised": {
    "Brow_Raise_Outer_L": 0.6, "Brow_Raise_Outer_R": 0.6,
    "Brow_Raise_Inner_L": 0.4, "Brow_Raise_Inner_R": 0.4,
    "Eye_Wide_L": 0.5, "Eye_Wide_R": 0.5,
    "Jaw_Open": 0.2, "Mouth_Drop_Lower": 0.15
  },
  "Concerned": {
    "Brow_Raise_Inner_L": 0.5, "Brow_Raise_Inner_R": 0.5,
    "Brow_Drop_L": 0.2, "Brow_Drop_R": 0.2,
    "Mouth_Frown_L": 0.25, "Mouth_Frown_R": 0.25,
    "Mouth_Stretch_L": 0.15, "Mouth_Stretch_R": 0.15
  },
  "Listening": {
    "Brow_Raise_Inner_L": 0.1, "Brow_Raise_Inner_R": 0.1,
    "Eye_Wide_L": 0.1, "Eye_Wide_R": 0.1,
    "Mouth_Smile_L": 0.1, "Mouth_Smile_R": 0.1
  },
  "Explaining": {
    "Brow_Raise_Outer_L": 0.2, "Brow_Raise_Outer_R": 0.2,
    "Eye_Wide_L": 0.15, "Eye_Wide_R": 0.15,
    "Mouth_Smile_L": 0.25, "Mouth_Smile_R": 0.25,
    "Cheek_Raise_L": 0.15, "Cheek_Raise_R": 0.15
  }
}
```

> Unreal 적용 공식: `final_weight = preset_weight * emotion_intensity * character_multiplier`

---

## Behavior JSON 매핑 요약

```json
{
  "facePreset": "Thinking",
  "emotionIntensity": 0.7,
  "gazeTarget": "user",
  "headMotion": "small_nod"
}
```

| JSON 필드 | 제어 morph 카테고리 | 담당 레이어 |
|---|---|---|
| `facePreset` + `emotionIntensity` | Brow, Cheek, Eye_Squint/Wide, Mouth_Smile/Frown 등 | Expression Layer |
| `gazeTarget` | Eye_L/R_Look_* | Gaze Layer |
| `headMotion` | Head_Turn/Tilt/Forward | Head Motion Layer |
| TTS viseme event | V_* morphs, Jaw_Open | LipSync Layer |
| idle (자동) | Eye_Blink_L/R | Idle/Blink Layer |

---

## 크기 차이 결론 및 권장 조치

1. **Physics Asset 재생성**: child_female_test1에 맞게 Physics Asset을 UE 에디터에서 regenerate. 시각적 크기와는 무관하지만 충돌/물리 정확도를 위해 필요.

2. **Import Scale 확인**: UE에서 두 SkeletalMesh의 Import Uniform Scale 값 비교 (`Content Browser → 우클릭 → Asset Actions → Reimport` 또는 Details 패널).

3. **CC4 Scale morph 확인**: child_female_test1의 `Scale` morph target 기본값 확인. non-zero면 캐릭터 설계 체형 자체가 다른 것.

4. **캐릭터 신장 차이**: CC4에서 의도적으로 더 작은 체형으로 만든 캐릭터일 가능성 있음 (child = 아이 캐릭터이므로 의도된 설계일 수 있음).
