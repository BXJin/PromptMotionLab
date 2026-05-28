#include "FacePresetResolver.h"

#include "FaceMorphDomains.h"

namespace
{
using FPresetMap = FFacePresetResolver::FPresetMap;

FPresetMap BuildFriendlyPreset()
{
    FPresetMap P;
    P.Add(TEXT("Mouth_Smile_L"), 0.80f); P.Add(TEXT("Mouth_Smile_R"), 0.80f);
    P.Add(TEXT("Cheek_Raise_L"), 0.50f); P.Add(TEXT("Cheek_Raise_R"), 0.50f);
    P.Add(TEXT("Eye_Squint_L"), 0.50f); P.Add(TEXT("Eye_Squint_R"), 0.50f);
    P.Add(TEXT("Eye_Wide_L"), 0.20f); P.Add(TEXT("Eye_Wide_R"), 0.20f);
    return P;
}

FPresetMap BuildHappyPreset()
{
    FPresetMap P;
    P.Add(TEXT("Mouth_Smile_L"), 1.00f); P.Add(TEXT("Mouth_Smile_R"), 1.00f);
    P.Add(TEXT("Cheek_Raise_L"), 1.00f); P.Add(TEXT("Cheek_Raise_R"), 1.00f);
    P.Add(TEXT("Eye_Squint_L"), 0.80f); P.Add(TEXT("Eye_Squint_R"), 0.80f);
    P.Add(TEXT("Eye_Wide_L"), 0.50f); P.Add(TEXT("Eye_Wide_R"), 0.50f);
    P.Add(TEXT("Nose_Crease_L"), 0.50f); P.Add(TEXT("Nose_Crease_R"), 0.50f);
    P.Add(TEXT("Brow_Raise_Outer_L"), 0.50f); P.Add(TEXT("Brow_Raise_Outer_R"), 0.50f);
    return P;
}

FPresetMap BuildThinkingPreset()
{
    FPresetMap P;
    P.Add(TEXT("Brow_Raise_Inner_L"), 1.00f); P.Add(TEXT("Brow_Raise_Inner_R"), 1.00f);
    P.Add(TEXT("Brow_Compress_L"), 0.70f); P.Add(TEXT("Brow_Compress_R"), 0.70f);
    P.Add(TEXT("Eye_Squint_L"), 0.60f); P.Add(TEXT("Eye_Squint_R"), 0.60f);
    P.Add(TEXT("Mouth_Tighten_L"), 0.80f); P.Add(TEXT("Mouth_Tighten_R"), 0.80f);
    P.Add(TEXT("Mouth_Press_L"), 0.60f); P.Add(TEXT("Mouth_Press_R"), 0.60f);
    P.Add(TEXT("Cheek_Suck_L"), 0.50f); P.Add(TEXT("Cheek_Suck_R"), 0.50f);
    return P;
}

FPresetMap BuildCuriousPreset()
{
    FPresetMap P;
    P.Add(TEXT("Brow_Raise_Inner_L"), 1.00f); P.Add(TEXT("Brow_Raise_Inner_R"), 1.00f);
    P.Add(TEXT("Brow_Raise_Outer_L"), 0.80f); P.Add(TEXT("Brow_Raise_Outer_R"), 0.80f);
    P.Add(TEXT("Eye_Wide_L"), 0.90f); P.Add(TEXT("Eye_Wide_R"), 0.90f);
    P.Add(TEXT("Mouth_Smile_L"), 0.30f); P.Add(TEXT("Mouth_Smile_R"), 0.30f);
    return P;
}

FPresetMap BuildConcernedPreset()
{
    FPresetMap P;
    P.Add(TEXT("Brow_Raise_Inner_L"), 1.00f); P.Add(TEXT("Brow_Raise_Inner_R"), 1.00f);
    P.Add(TEXT("Brow_Compress_L"), 0.60f); P.Add(TEXT("Brow_Compress_R"), 0.60f);
    P.Add(TEXT("Brow_Drop_L"), 0.70f); P.Add(TEXT("Brow_Drop_R"), 0.70f);
    P.Add(TEXT("Eye_Wide_L"), 0.45f); P.Add(TEXT("Eye_Wide_R"), 0.45f);
    P.Add(TEXT("Mouth_Frown_L"), 1.00f); P.Add(TEXT("Mouth_Frown_R"), 1.00f);
    return P;
}

FPresetMap BuildUncertainPreset()
{
    FPresetMap P;
    P.Add(TEXT("Brow_Raise_Inner_L"), 1.00f); P.Add(TEXT("Brow_Raise_Inner_R"), 1.00f);
    P.Add(TEXT("Brow_Compress_L"), 0.40f); P.Add(TEXT("Brow_Compress_R"), 0.40f);
    P.Add(TEXT("Eye_Squint_L"), 0.50f); P.Add(TEXT("Eye_Squint_R"), 0.50f);
    P.Add(TEXT("Eye_Wide_L"), 0.30f); P.Add(TEXT("Eye_Wide_R"), 0.30f);
    P.Add(TEXT("Mouth_Tighten_L"), 0.60f); P.Add(TEXT("Mouth_Tighten_R"), 0.60f);
    P.Add(TEXT("Mouth_Press_L"), 0.40f); P.Add(TEXT("Mouth_Press_R"), 0.40f);
    P.Add(TEXT("Cheek_Suck_L"), 0.30f); P.Add(TEXT("Cheek_Suck_R"), 0.30f);
    return P;
}

FPresetMap BuildApologeticPreset()
{
    FPresetMap P;
    P.Add(TEXT("Brow_Raise_Inner_L"), 1.00f); P.Add(TEXT("Brow_Raise_Inner_R"), 1.00f);
    P.Add(TEXT("Brow_Drop_L"), 1.00f); P.Add(TEXT("Brow_Drop_R"), 1.00f);
    P.Add(TEXT("Eye_Squint_L"), 0.60f); P.Add(TEXT("Eye_Squint_R"), 0.60f);
    P.Add(TEXT("Mouth_Frown_L"), 0.90f); P.Add(TEXT("Mouth_Frown_R"), 0.90f);
    P.Add(TEXT("Mouth_Press_L"), 0.60f); P.Add(TEXT("Mouth_Press_R"), 0.60f);
    return P;
}

FPresetMap BuildListeningPreset()
{
    FPresetMap P;
    P.Add(TEXT("Eye_Squint_L"), 0.14f); P.Add(TEXT("Eye_Squint_R"), 0.14f);
    P.Add(TEXT("Brow_Raise_Inner_L"), 0.18f); P.Add(TEXT("Brow_Raise_Inner_R"), 0.18f);
    P.Add(TEXT("Mouth_Smile_L"), 0.12f); P.Add(TEXT("Mouth_Smile_R"), 0.12f);
    return P;
}

FPresetMap BuildExplainingPreset()
{
    FPresetMap P;
    P.Add(TEXT("Eye_Wide_L"), 0.16f); P.Add(TEXT("Eye_Wide_R"), 0.16f);
    P.Add(TEXT("Brow_Raise_Outer_L"), 0.18f); P.Add(TEXT("Brow_Raise_Outer_R"), 0.18f);
    P.Add(TEXT("Mouth_Smile_L"), 0.16f); P.Add(TEXT("Mouth_Smile_R"), 0.16f);
    return P;
}

FPresetMap BuildSurprisedPreset()
{
    FPresetMap P;
    P.Add(TEXT("Eye_Wide_L"), 0.56f); P.Add(TEXT("Eye_Wide_R"), 0.56f);
    P.Add(TEXT("Brow_Raise_Inner_L"), 0.52f); P.Add(TEXT("Brow_Raise_Inner_R"), 0.52f);
    P.Add(TEXT("Brow_Raise_Outer_L"), 0.42f); P.Add(TEXT("Brow_Raise_Outer_R"), 0.42f);
    return P;
}

FString GCachedCharacterId;
TMap<FString, FPresetMap> GCachedCsvPresets;
FPromptMotionFaceConfig::FFacePresetSettingsMap GCachedCsvPresetSettings;

float DefaultLipSyncKeepRatioForMorph(FName MorphName)
{
    const FString Name = MorphName.ToString();
    if (Name.StartsWith(TEXT("Mouth_Press")) || Name.StartsWith(TEXT("Mouth_Tighten")))
        return 0.15f;
    if (Name.StartsWith(TEXT("Mouth_Pucker")))
        return 0.20f;
    if (Name.StartsWith(TEXT("Mouth_")))
        return 0.65f;
    if (Name.StartsWith(TEXT("Cheek_Suck")))
        return 0.60f;
    return 1.0f;
}

FPromptMotionFaceMorphSetting MakeFallbackSetting(FName MorphName, float Weight)
{
    FPromptMotionFaceMorphSetting Setting;
    Setting.Weight = Weight;
    Setting.LipSyncMask = DefaultLipSyncKeepRatioForMorph(MorphName);
    return Setting;
}
}

const TMap<FString, FFacePresetResolver::FPresetMap>& FFacePresetResolver::GetPresets()
{
    static const TMap<FString, FPresetMap> Presets = []()
    {
        TMap<FString, FPresetMap> P;
        P.Add(TEXT("Neutral"), FPresetMap{});
        P.Add(TEXT("Friendly"), BuildFriendlyPreset());
        P.Add(TEXT("Happy"), BuildHappyPreset());
        P.Add(TEXT("Thinking"), BuildThinkingPreset());
        P.Add(TEXT("Curious"), BuildCuriousPreset());
        P.Add(TEXT("Concerned"), BuildConcernedPreset());
        P.Add(TEXT("Uncertain"), BuildUncertainPreset());
        P.Add(TEXT("Apologetic"), BuildApologeticPreset());
        P.Add(TEXT("Listening"), BuildListeningPreset());
        P.Add(TEXT("Explaining"), BuildExplainingPreset());
        P.Add(TEXT("Surprised"), BuildSurprisedPreset());

#if !UE_BUILD_SHIPPING
        for (const auto& Pair : P)
            FFaceMorphDomains::ValidateNoConflict(Pair.Value, Pair.Key);
#endif
        return P;
    }();
    return Presets;
}

void FFacePresetResolver::LoadCsvForCharacter(const FString& CharacterId)
{
    FPromptMotionFaceConfig::FFacePresetSettingsMap Loaded;
    if (!FPromptMotionFaceConfig::LoadFacePresetSettings(CharacterId, Loaded))
    {
        GCachedCharacterId.Empty();
        GCachedCsvPresets.Reset();
        GCachedCsvPresetSettings.Reset();
        return;
    }

    GCachedCsvPresets.Reset();
    GCachedCsvPresetSettings = Loaded;
    for (const auto& Pair : Loaded)
    {
        FPresetMap& CachedPreset = GCachedCsvPresets.FindOrAdd(Pair.Key);
        for (const auto& MorphPair : Pair.Value)
            CachedPreset.FindOrAdd(MorphPair.Key) = MorphPair.Value.Weight;

#if !UE_BUILD_SHIPPING
        FFaceMorphDomains::ValidateNoConflict(CachedPreset, Pair.Key);
#endif
    }
    GCachedCharacterId = CharacterId;
}

FFacePresetResolver::FPresetMap FFacePresetResolver::BuildFullResetMap(const TMap<FString, FPresetMap>& Presets)
{
    FPresetMap M;
    for (const auto& PresetPair : Presets)
        for (const auto& MorphPair : PresetPair.Value)
            M.FindOrAdd(MorphPair.Key) = 0.0f;
    return M;
}

const FFacePresetResolver::FPresetMap& FFacePresetResolver::GetFullResetMap()
{
    static const FPresetMap ResetMap = []()
    {
        return BuildFullResetMap(GetPresets());
    }();
    return ResetMap;
}

FString FFacePresetResolver::EmotionToPresetKey(const FString& Emotion)
{
    static const TMap<FString, FString> KeyMap =
    {
        { TEXT("neutral"), TEXT("Neutral") },
        { TEXT("friendly"), TEXT("Friendly") },
        { TEXT("happy"), TEXT("Happy") },
        { TEXT("thinking"), TEXT("Thinking") },
        { TEXT("curious"), TEXT("Curious") },
        { TEXT("concerned"), TEXT("Concerned") },
        { TEXT("uncertain"), TEXT("Uncertain") },
        { TEXT("apologetic"), TEXT("Apologetic") },
        { TEXT("listening"), TEXT("Listening") },
        { TEXT("explaining"), TEXT("Explaining") },
        { TEXT("surprised"), TEXT("Surprised") },
    };

    const FString* Found = KeyMap.Find(Emotion.ToLower());
    return Found ? *Found : TEXT("Neutral");
}

float FFacePresetResolver::QueryWeight(const FString& Preset, FName MorphName, const FString& CharacterId)
{
    return QuerySetting(Preset, MorphName, CharacterId).Weight;
}

FPromptMotionFaceMorphSetting FFacePresetResolver::QuerySetting(const FString& Preset, FName MorphName, const FString& CharacterId)
{
    if (!CharacterId.IsEmpty() && GCachedCharacterId == CharacterId && !GCachedCsvPresetSettings.IsEmpty())
    {
        if (const TMap<FName, FPromptMotionFaceMorphSetting>* CsvPreset = GCachedCsvPresetSettings.Find(Preset))
        {
            if (const FPromptMotionFaceMorphSetting* Found = CsvPreset->Find(MorphName))
                return *Found;
            return FPromptMotionFaceMorphSetting{};
        }
    }

    if (const FPresetMap* HardPreset = GetPresets().Find(Preset))
    {
        const float* Found = HardPreset->Find(MorphName);
        return Found ? MakeFallbackSetting(MorphName, *Found) : FPromptMotionFaceMorphSetting{};
    }
    return FPromptMotionFaceMorphSetting{};
}

TMap<FName, float> FFacePresetResolver::Resolve(const FString& Emotion, float Intensity)
{
    TMap<FName, float> Result = GetFullResetMap();
    const FString PresetKey = EmotionToPresetKey(Emotion);
    const FPresetMap* Preset = GetPresets().Find(PresetKey);
    if (!Preset || Preset->IsEmpty())
        return Result;

    const float ClampedIntensity = FMath::Clamp(Intensity, 0.0f, 2.0f);
    for (const auto& Pair : *Preset)
        Result.FindOrAdd(Pair.Key) = Pair.Value * ClampedIntensity;
    return Result;
}

TMap<FName, float> FFacePresetResolver::Resolve(const FString& Emotion, float Intensity, const FString& CharacterId)
{
    TMap<FName, float> Result;
    for (const auto& Pair : ResolveSettings(Emotion, Intensity, CharacterId))
        Result.FindOrAdd(Pair.Key) = Pair.Value.Weight;
    return Result;
}

TMap<FName, FPromptMotionFaceMorphSetting> FFacePresetResolver::ResolveSettings(
    const FString& Emotion,
    float Intensity,
    const FString& CharacterId)
{
    TMap<FName, FPromptMotionFaceMorphSetting> Result;
    const FString PresetKey = EmotionToPresetKey(Emotion);
    const float ClampedIntensity = FMath::Clamp(Intensity, 0.0f, 2.0f);

    if (!GCachedCsvPresetSettings.IsEmpty() && GCachedCharacterId == CharacterId)
    {
        for (const auto& PresetPair : GCachedCsvPresetSettings)
            for (const auto& MorphPair : PresetPair.Value)
                Result.FindOrAdd(MorphPair.Key) = FPromptMotionFaceMorphSetting{};

        const TMap<FName, FPromptMotionFaceMorphSetting>* Preset = GCachedCsvPresetSettings.Find(PresetKey);
        if (!Preset)
        {
            if (const FPresetMap* FallbackPreset = GetPresets().Find(PresetKey))
            {
                for (const auto& Pair : *FallbackPreset)
                    Result.FindOrAdd(Pair.Key) = MakeFallbackSetting(Pair.Key, Pair.Value * ClampedIntensity);
            }
            return Result;
        }

        for (const auto& Pair : *Preset)
        {
            FPromptMotionFaceMorphSetting Setting = Pair.Value;
            Setting.Weight *= ClampedIntensity;
            Result.FindOrAdd(Pair.Key) = Setting;
        }
        return Result;
    }

    for (const auto& PresetPair : GetPresets())
        for (const auto& MorphPair : PresetPair.Value)
            Result.FindOrAdd(MorphPair.Key) = FPromptMotionFaceMorphSetting{};

    const FPresetMap* Preset = GetPresets().Find(PresetKey);
    if (!Preset)
        return Result;

    for (const auto& Pair : *Preset)
        Result.FindOrAdd(Pair.Key) = MakeFallbackSetting(Pair.Key, Pair.Value * ClampedIntensity);
    return Result;
}
