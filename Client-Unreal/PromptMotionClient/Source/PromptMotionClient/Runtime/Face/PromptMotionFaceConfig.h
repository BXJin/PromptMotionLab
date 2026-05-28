#pragma once

#include "CoreMinimal.h"

struct FPromptMotionMorphWeight
{
    FName MorphName;
    float Weight = 0.0f;
    float FadeInSec = 0.05f;
    float FadeOutSec = 0.08f;
};

struct FPromptMotionFaceMorphSetting
{
    float Weight = 0.0f;
    FString BlendMode = TEXT("Additive");
    float FadeInSec = 0.18f;
    float FadeOutSec = 0.24f;
    float LipSyncMask = 0.0f;
    FName ConflictGroup;
};

class FPromptMotionFaceConfig
{
public:
    using FFacePresetMap = TMap<FString, TMap<FName, float>>;
    using FFacePresetSettingsMap = TMap<FString, TMap<FName, FPromptMotionFaceMorphSetting>>;
    using FLipSyncVisemeMap = TMap<int32, TArray<FPromptMotionMorphWeight>>;

    static FString GetPromptMotionConfigDir();
    static FString GetFacePresetCsvPath(const FString& CharacterId);
    static FString GetLipSyncVisemeCsvPath(const FString& CharacterId);

    static bool LoadFacePresets(const FString& CharacterId, FFacePresetMap& OutPresets);
    static bool LoadFacePresetSettings(const FString& CharacterId, FFacePresetSettingsMap& OutPresets);
    static bool LoadLipSyncVisemes(const FString& CharacterId, FLipSyncVisemeMap& OutVisemes);
};
