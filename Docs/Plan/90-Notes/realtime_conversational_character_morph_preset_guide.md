# 실시간 대화형 캐릭터 Morph Preset 설계 가이드

작성 기준: **실시간 대화 + 립싱크 + 자연스러운 표정**  
대상: Unreal Engine 캐릭터, CC4/Reallusion 계열 morph target, CSV 런타임 로드 방식  
생성 파일: `realtime_conversational_character_morph_presets.csv`

---

## 1. 결론

이 문서는 **DataTable 고정 사용**이 아니라, 먼저 **CSV를 직접 로드해서 런타임 캐시로 사용하는 방식**을 기준으로 설계했다.

권장 방식은 다음 순서다.

```text
CSV 파일
  ↓
C++ 또는 Blueprint 유틸에서 파싱
  ↓
TMap<FName, TArray<FMorphPresetRow>> 형태로 캐싱
  ↓
Expression / LipSync / Blink / Gaze / Jaw / HeadMotion 레이어별 resolve
  ↓
USkeletalMeshComponent::SetMorphTarget 또는 AnimBP Curve로 적용
```

DataTable은 나쁜 방식이 아니다. 다만 지금 프로젝트처럼 **외부 CSV를 수정하고 바로 반영하고 싶은 구조**라면, 런타임 CSV 로더가 더 유연하다. DataTable은 에디터 import/검증/디자이너 친화성이 중요할 때 선택하면 된다.

---

## 2. 설계 기준

실시간 대화형 캐릭터 기준에서는 단순 감정 preset만으로는 부족하다.

필요 레이어는 다음과 같다.

| Layer | 역할 | 우선순위 |
|---|---|---:|
| `LipSync` | TTS/음성 기반 viseme, `V_*`, `Jaw_Open` | 90 |
| `Jaw` | 입 열림/닫힘 보정 | 70 |
| `IdleBlink` | 눈깜빡임, 미세 눈 움직임 | 60 |
| `Gaze` | 시선 방향 | 50 |
| `HeadMotion` | 고개 보조 움직임 | 40 |
| `Expression` | 감정 preset | 30 |

가장 중요한 원칙은 **립싱크가 입/턱을 우선 제어하고, 감정 표정은 그 아래에서 유지되는 구조**다.

```text
LipSync > Jaw > Blink/Gaze > HeadMotion > Expression
```

---

## 3. 왜 CSV 직접 로드 방식인가?

### CSV 직접 로드가 좋은 경우

| 상황 | 판단 |
|---|---|
| 외부 파일을 바꿔서 바로 테스트하고 싶다 | 적합 |
| 기획자가 Excel/CSV로 weight를 조정한다 | 적합 |
| 서버에서 preset CSV를 내려받을 가능성이 있다 | 적합 |
| 패키징 후에도 preset 값을 바꾸고 싶다 | 적합 |
| CSV schema가 자주 바뀐다 | 적합 |

### DataTable이 더 좋은 경우

| 상황 | 판단 |
|---|---|
| Unreal Editor 안에서 검증하고 싶다 | DataTable 유리 |
| RowStruct 기반 타입 안정성이 필요하다 | DataTable 유리 |
| 패키징된 고정 데이터로만 쓴다 | DataTable 유리 |
| 디자이너가 Editor에서 관리한다 | DataTable 유리 |

### 추천 판단

현재 프로젝트는 **CSV 직접 로드 우선**이 맞다.  
단, C++에서 CSV를 읽은 뒤 내부 구조체로 변환하면 DataTable처럼 쓸 수 있다.

즉 최종 형태는 이게 좋다.

```text
외부 파일 포맷은 CSV
내부 사용 방식은 DataTable처럼 TMap 캐시
```

---

## 4. CSV 컬럼 설명

| 컬럼 | 설명 |
|---|---|
| `preset_id` | `Happy`, `Thinking`, `Viseme_AA_AH` 같은 preset 이름 |
| `preset_type` | `expression`, `viseme`, `idle`, `gaze`, `jaw`, `head` |
| `layer` | 런타임 resolve 레이어 |
| `morph_name` | Unreal SkeletalMesh에 존재하는 morph target 이름 |
| `base_weight` | 기본 weight. 보통 0.0~1.0 |
| `min_weight` | clamp 최소값 |
| `max_weight` | clamp 최대값 |
| `priority` | 레이어 충돌 시 우선순위 |
| `fade_in_sec` | 목표값까지 올라가는 시간 |
| `fade_out_sec` | 빠지는 시간 |
| `blend_mode` | `Additive` 또는 `Override` |
| `conflict_group` | 서로 충돌하는 morph 그룹 |
| `lip_sync_mask` | 립싱크 중 expression mouth 계열을 줄이는 비율 |
| `character_multiplier` | 캐릭터별 보정값 |
| `notes_ko` | 한글 설명 |

---

## 5. 포함된 preset 범위

이번 CSV는 다음 기준으로 만들었다.

| 분류 | preset |
|---|---|
| 기본 감정 | `Neutral`, `Listening`, `Friendly`, `Happy`, `Thinking`, `Curious`, `Concerned`, `Uncertain`, `Apologetic`, `Surprised`, `Explaining` |
| 눈/idle | `Blink_Both`, `Blink_Left`, `Blink_Right`, `Micro_Squint` |
| 시선 | `Gaze_Left`, `Gaze_Right`, `Gaze_Up`, `Gaze_Down`, `Gaze_User` |
| 턱/입 보정 | `Jaw_Relaxed`, `Jaw_SmallOpen`, `Mouth_Closed` |
| 립싱크 | `Viseme_AA_AH`, `Viseme_EH_AE`, `Viseme_OH_OW`, `Viseme_UW_OO`, `Viseme_FV`, `Viseme_PBM`, `Viseme_CH_J`, `Viseme_TH`, `Viseme_L_N`, `Viseme_S_Z`, `Viseme_R`, `Viseme_Rest` |
| 고개 보조 | `Head_SmallNod`, `Head_Tilt_Left`, `Head_Tilt_Right` |

---

## 6. 사용 morph 수

이번 CSV 기준:

| 항목 | 수 |
|---|---:|
| CSV row 수 | 195 |
| unique morph 수 | 62 |
| layer 수 | 6 |

Layer별 unique morph 수:

- `Expression`: 34개
- `Gaze`: 8개
- `HeadMotion`: 4개
- `IdleBlink`: 6개
- `Jaw`: 2개
- `LipSync`: 14개

실시간 대화형 캐릭터 기준으로는 이 정도가 적당하다.  
처음부터 EO/TL/Eyelash 전체를 직접 제어하지 않고, 핵심 표정 + blink + gaze + viseme 중심으로 시작하는 것이 안전하다.

---

## 7. 런타임 적용 공식

기본 계산식은 다음처럼 잡는다.

```text
raw = base_weight * emotion_intensity * character_multiplier
masked = raw * lip_sync_mask
final = clamp(masked, min_weight, max_weight)
```

단, `LipSync`, `Jaw`, `Gaze`, `Blink`는 보통 `Override` 성격이 강하다.

```text
Expression: Additive 중심
LipSync: Override 중심
Jaw: Override 중심
Blink: Override 중심
Gaze: Override 중심
HeadMotion: Additive 또는 bone 우선
```

---

## 8. C++ 로딩 구조 예시

실제 구현에서는 CSV를 매 tick마다 읽으면 안 된다.  
게임 시작 시 또는 캐릭터 초기화 시 한 번 읽고 캐싱한다.

```cpp
USTRUCT()
struct FMorphPresetRow
{
    GENERATED_BODY()

    FName PresetId;
    FName PresetType;
    FName Layer;
    FName MorphName;
    float BaseWeight = 0.f;
    float MinWeight = 0.f;
    float MaxWeight = 1.f;
    int32 Priority = 0;
    float FadeInSec = 0.1f;
    float FadeOutSec = 0.1f;
    FName BlendMode;
    FName ConflictGroup;
    float LipSyncMask = 1.f;
    float CharacterMultiplier = 1.f;
    FString NotesKo;
};

TMap<FName, TArray<FMorphPresetRow>> PresetMap;
```

추천 캐시 구조:

```cpp
TMap<FName, TArray<FMorphPresetRow>> PresetMap;
TMap<FName, float> CurrentMorphWeights;
TMap<FName, float> TargetMorphWeights;
```

적용 흐름:

```text
1. CSV 로드
2. preset_id 기준으로 TMap 구성
3. 서버/LLM에서 facePreset, emotionIntensity 수신
4. preset_id에 해당하는 morph 목록 조회
5. layer priority 순서대로 target weight 계산
6. fade_in/fade_out 기준으로 current weight 보간
7. SkeletalMeshComponent->SetMorphTarget(MorphName, CurrentWeight)
```

---

## 9. DataTable을 쓸지 말지에 대한 판단

DataTable은 “진짜 좋은 방법”인 경우에만 쓰면 된다.

### 지금은 CSV 직접 로드 추천

이유:

- 외부 파일 수정 후 빠르게 테스트 가능
- 서버/런타임 업데이트 가능성 있음
- preset schema를 바꾸기 쉬움
- DataTable import 과정을 매번 거치지 않아도 됨

### 나중에 DataTable 전환을 고려할 시점

- preset이 안정화됨
- 에디터에서 행 검증이 필요함
- RowStruct 기반 자동 검증이 필요함
- 디자이너가 Unreal Editor 안에서 관리해야 함
- 패키징 이후 외부 수정이 필요 없음

### 절충안

가장 좋은 절충안은 다음이다.

```text
개발/튜닝 단계: 외부 CSV 직접 로드
릴리즈 고정 데이터: DataTable import 또는 내부 asset화
```

---

## 10. 립싱크 충돌 규칙

입 관련 expression morph는 립싱크 중 그대로 두면 입이 찢어질 수 있다.

예:

```text
Happy.Mouth_Smile_L = 0.55
Viseme_AA_AH.Jaw_Open = 0.42
```

이 둘을 단순 합산하면 말할 때 입꼬리가 과하게 벌어질 수 있다.

그래서 CSV의 `lip_sync_mask`를 사용한다.

```text
final_expression_mouth = expression_mouth * lip_sync_mask
```

예:

```text
0.55 * 0.70 = 0.385
```

즉 말하는 중에도 웃는 느낌은 남기되, 입 모양을 립싱크가 우선하게 한다.

---

## 11. Head/Gaze는 morph보다 bone 우선

CSV에는 `Head_Tilt`, `Head_Forward`, `Eye_Look` 계열을 넣어두었지만, 실제 구현에서는 다음 기준이 좋다.

| 대상 | 우선 방식 |
|---|---|
| 눈동자 방향 | Eye bone/control rig 우선, morph 보조 |
| 고개 회전 | Neck/Head bone 우선, morph 보조 |
| 미세한 눈꺼풀/눈 주변 변화 | morph 사용 |
| 감정 표정 | morph 사용 |
| 립싱크 | morph 사용 |

---

## 12. 구현 단계 추천

### Phase 1

- CSV 직접 로드
- `Expression`, `LipSync`, `Jaw`만 적용
- `SetMorphTarget`으로 테스트

### Phase 2

- `Blink`, `Gaze` 추가
- 현재값/목표값 보간
- conflict group 처리

### Phase 3

- TTS viseme event 연동
- lip_sync_mask 적용
- 말하는 중 expression mouth 제한

### Phase 4

- 캐릭터별 multiplier 추가
- DataTable 또는 asset화 여부 판단
- AnimBP Curve/Control Rig 연동 검토

---

## 13. 최종 추천

현재 목표에서는 **CSV 직접 로드 + 내부 TMap 캐시**가 가장 적절하다.

DataTable은 버리는 게 아니라, 나중에 preset이 안정화되었을 때 선택할 수 있는 옵션이다.  
지금은 구현 속도와 튜닝 편의성이 더 중요하므로 CSV를 기준으로 진행하는 것이 좋다.
