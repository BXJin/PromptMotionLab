#include "FacePresetResolver.h"
#include "FaceMorphDomains.h"

// ---------------------------------------------------------------------------
// Preset 빌더 (CHARACTER-MORPH-TARGET-CATALOG.md 기준)
// 공식: FinalWeight = PresetBaseWeight * Intensity
// ---------------------------------------------------------------------------

static TMap<FName, float> BuildSmilePreset()
{
    TMap<FName, float> P;
    P.Add(TEXT("Mouth_Smile_L"), 0.60f);
    P.Add(TEXT("Mouth_Smile_R"), 0.60f);
    P.Add(TEXT("Cheek_Raise_L"), 0.40f);
    P.Add(TEXT("Cheek_Raise_R"), 0.40f);
    P.Add(TEXT("Eye_Squint_L"),  0.20f);
    P.Add(TEXT("Eye_Squint_R"),  0.20f);
    P.Add(TEXT("Nose_Crease_L"), 0.15f);
    P.Add(TEXT("Nose_Crease_R"), 0.15f);
    return P;
}

static TMap<FName, float> BuildThinkingPreset()
{
    TMap<FName, float> P;
    P.Add(TEXT("Brow_Raise_Inner_L"), 0.55f);
    P.Add(TEXT("Brow_Raise_Inner_R"), 0.55f);
    P.Add(TEXT("Brow_Compress_L"),    0.35f);
    P.Add(TEXT("Brow_Compress_R"),    0.35f);
    P.Add(TEXT("Eye_Squint_L"),       0.20f);
    P.Add(TEXT("Eye_Squint_R"),       0.20f);
    P.Add(TEXT("Mouth_Tighten_L"),    0.40f);
    P.Add(TEXT("Mouth_Tighten_R"),    0.40f);
    P.Add(TEXT("Mouth_Press_L"),      0.30f);
    P.Add(TEXT("Mouth_Press_R"),      0.30f);
    P.Add(TEXT("Cheek_Suck_L"),       0.25f);
    P.Add(TEXT("Cheek_Suck_R"),       0.25f);
    return P;
}

static TMap<FName, float> BuildConcernedPreset()
{
    TMap<FName, float> P;
    P.Add(TEXT("Brow_Raise_Inner_L"), 0.75f);
    P.Add(TEXT("Brow_Raise_Inner_R"), 0.75f);
    P.Add(TEXT("Brow_Compress_L"),    0.30f);
    P.Add(TEXT("Brow_Compress_R"),    0.30f);
    P.Add(TEXT("Brow_Drop_L"),        0.35f);
    P.Add(TEXT("Brow_Drop_R"),        0.35f);
    P.Add(TEXT("Mouth_Frown_L"),      0.50f);
    P.Add(TEXT("Mouth_Frown_R"),      0.50f);
    return P;
}

// ---------------------------------------------------------------------------

const TMap<FString, FFacePresetResolver::FPresetMap>& FFacePresetResolver::GetPresets()
{
    static const TMap<FString, FPresetMap> Presets = []()
    {
        TMap<FString, FPresetMap> P;
        P.Add(TEXT("Neutral"),   FPresetMap{});
        P.Add(TEXT("Smile"),     BuildSmilePreset());
        P.Add(TEXT("Thinking"),  BuildThinkingPreset());
        P.Add(TEXT("Concerned"), BuildConcernedPreset());

        // 도메인 충돌 검증 — 최초 1회, Shipping 제외
        // Expression preset에 LipSync/Idle morph가 섞이면 여기서 즉시 잡힌다.
#if !UE_BUILD_SHIPPING
        for (const auto& Pair : P)
        {
            FFaceMorphDomains::ValidateNoConflict(Pair.Value, Pair.Key);
        }
#endif

        return P;
    }();
    return Presets;
}

const FFacePresetResolver::FPresetMap& FFacePresetResolver::GetFullResetMap()
{
    static const FPresetMap ResetMap = []()
    {
        FPresetMap M;
        // 모든 preset에 등장하는 morph를 수집 → 이전 표정 잔류 방지
        for (const auto& PresetPair : GetPresets())
        {
            for (const auto& MorphPair : PresetPair.Value)
            {
                M.FindOrAdd(MorphPair.Key) = 0.0f;
            }
        }
        return M;
    }();
    return ResetMap;
}

FString FFacePresetResolver::EmotionToPresetKey(const FString& Emotion)
{
    if (Emotion == TEXT("friendly") || Emotion == TEXT("happy"))
        return TEXT("Smile");

    if (Emotion == TEXT("thinking") || Emotion == TEXT("curious") || Emotion == TEXT("uncertain"))
        return TEXT("Thinking");

    if (Emotion == TEXT("concerned") || Emotion == TEXT("apologetic"))
        return TEXT("Concerned");

    return TEXT("Neutral");
}

TMap<FName, float> FFacePresetResolver::Resolve(const FString& Emotion, float Intensity)
{
    // 1. 전체 morph 초기화 맵에서 시작 (이전 preset 잔류 제거)
    TMap<FName, float> Result = GetFullResetMap();

    // 2. emotion → preset 키
    const FString PresetKey = EmotionToPresetKey(Emotion);
    const FPresetMap* Preset = GetPresets().Find(PresetKey);
    if (!Preset || Preset->IsEmpty())
        return Result;  // Neutral → 전부 0 반환

    // 3. base weight * intensity 적용
    const float ClampedIntensity = FMath::Clamp(Intensity, 0.0f, 1.0f);
    for (const auto& Pair : *Preset)
    {
        Result.FindOrAdd(Pair.Key) = Pair.Value * ClampedIntensity;
    }

    return Result;
}
