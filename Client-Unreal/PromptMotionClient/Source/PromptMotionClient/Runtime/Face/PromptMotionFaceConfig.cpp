#include "PromptMotionFaceConfig.h"

#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
FString NormalizeCharacterId(const FString& CharacterId)
{
    return CharacterId.IsEmpty() ? TEXT("default_girl") : CharacterId;
}

void SplitCsvLine(const FString& Line, TArray<FString>& OutCells)
{
    OutCells.Reset();

    FString Current;
    bool bInQuotes = false;

    for (int32 Index = 0; Index < Line.Len(); ++Index)
    {
        const TCHAR C = Line[Index];
        if (C == TEXT('"'))
        {
            if (bInQuotes && Index + 1 < Line.Len() && Line[Index + 1] == TEXT('"'))
            {
                Current.AppendChar(TEXT('"'));
                ++Index;
            }
            else
            {
                bInQuotes = !bInQuotes;
            }
        }
        else if (C == TEXT(',') && !bInQuotes)
        {
            OutCells.Add(Current.TrimStartAndEnd());
            Current.Reset();
        }
        else
        {
            Current.AppendChar(C);
        }
    }

    OutCells.Add(Current.TrimStartAndEnd());
}

bool TryParseWeight(const FString& Text, float& OutWeight)
{
    if (!Text.IsNumeric())
        return false;

    OutWeight = FCString::Atof(*Text);
    return true;
}

float ParseOptionalFloat(const TArray<FString>& Cells, int32 Index, float DefaultValue, float MinValue, float MaxValue)
{
    if (!Cells.IsValidIndex(Index) || Cells[Index].IsEmpty())
        return DefaultValue;

    float Value = 0.0f;
    if (!TryParseWeight(Cells[Index], Value))
        return DefaultValue;

    return FMath::Clamp(Value, MinValue, MaxValue);
}

FString ParseOptionalString(const TArray<FString>& Cells, int32 Index, const FString& DefaultValue)
{
    if (!Cells.IsValidIndex(Index) || Cells[Index].IsEmpty())
        return DefaultValue;

    return Cells[Index].TrimStartAndEnd();
}

float DefaultLipSyncMaskForMorph(FName MorphName)
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
}

FString FPromptMotionFaceConfig::GetPromptMotionConfigDir()
{
    return FPaths::Combine(FPaths::ProjectConfigDir(), TEXT("PromptMotion"));
}

FString FPromptMotionFaceConfig::GetFacePresetCsvPath(const FString& CharacterId)
{
    return FPaths::Combine(
        GetPromptMotionConfigDir(),
        FString::Printf(TEXT("face_presets_%s.csv"), *NormalizeCharacterId(CharacterId)));
}

FString FPromptMotionFaceConfig::GetLipSyncVisemeCsvPath(const FString& CharacterId)
{
    return FPaths::Combine(
        GetPromptMotionConfigDir(),
        FString::Printf(TEXT("lipsync_visemes_%s.csv"), *NormalizeCharacterId(CharacterId)));
}

bool FPromptMotionFaceConfig::LoadFacePresets(const FString& CharacterId, FFacePresetMap& OutPresets)
{
    OutPresets.Reset();

    FFacePresetSettingsMap Settings;
    if (!LoadFacePresetSettings(CharacterId, Settings))
        return false;

    for (const auto& PresetPair : Settings)
    {
        TMap<FName, float>& Preset = OutPresets.FindOrAdd(PresetPair.Key);
        for (const auto& MorphPair : PresetPair.Value)
            Preset.FindOrAdd(MorphPair.Key) = MorphPair.Value.Weight;
    }

    return !OutPresets.IsEmpty();
}

bool FPromptMotionFaceConfig::LoadFacePresetSettings(const FString& CharacterId, FFacePresetSettingsMap& OutPresets)
{
    OutPresets.Reset();

    TArray<FString> Lines;
    if (!FFileHelper::LoadFileToStringArray(Lines, *GetFacePresetCsvPath(CharacterId)))
        return false;

    for (int32 LineIndex = 0; LineIndex < Lines.Num(); ++LineIndex)
    {
        FString Line = Lines[LineIndex].TrimStartAndEnd();
        if (Line.IsEmpty() || Line.StartsWith(TEXT("#")))
            continue;
        if (LineIndex == 0 && Line.StartsWith(TEXT("preset"), ESearchCase::IgnoreCase))
            continue;

        TArray<FString> Cells;
        SplitCsvLine(Line, Cells);
        if (Cells.Num() < 3)
            continue;

        float Weight = 0.0f;
        if (!TryParseWeight(Cells[2], Weight))
            continue;

        const FString Preset = Cells[0].TrimStartAndEnd();
        const FName MorphName(*Cells[1].TrimStartAndEnd());
        if (Preset.IsEmpty() || MorphName.IsNone())
            continue;

        FPromptMotionFaceMorphSetting Setting;
        Setting.Weight = FMath::Clamp(Weight, -1.0f, 1.0f);
        Setting.BlendMode = ParseOptionalString(Cells, 3, TEXT("Additive"));
        Setting.FadeInSec = ParseOptionalFloat(Cells, 4, 0.18f, 0.0f, 2.0f);
        Setting.FadeOutSec = ParseOptionalFloat(Cells, 5, 0.24f, 0.0f, 2.0f);
        Setting.LipSyncMask = ParseOptionalFloat(Cells, 6, DefaultLipSyncMaskForMorph(MorphName), 0.0f, 1.0f);
        Setting.ConflictGroup = FName(*ParseOptionalString(Cells, 7, TEXT("")));
        OutPresets.FindOrAdd(Preset).FindOrAdd(MorphName) = Setting;
    }

    return !OutPresets.IsEmpty();
}

bool FPromptMotionFaceConfig::LoadLipSyncVisemes(const FString& CharacterId, FLipSyncVisemeMap& OutVisemes)
{
    OutVisemes.Reset();

    TArray<FString> Lines;
    if (!FFileHelper::LoadFileToStringArray(Lines, *GetLipSyncVisemeCsvPath(CharacterId)))
        return false;

    for (int32 LineIndex = 0; LineIndex < Lines.Num(); ++LineIndex)
    {
        FString Line = Lines[LineIndex].TrimStartAndEnd();
        if (Line.IsEmpty() || Line.StartsWith(TEXT("#")))
            continue;
        if (LineIndex == 0 && Line.StartsWith(TEXT("viseme_id"), ESearchCase::IgnoreCase))
            continue;

        TArray<FString> Cells;
        SplitCsvLine(Line, Cells);
        if (Cells.Num() < 3 || !Cells[0].IsNumeric())
            continue;

        float Weight = 0.0f;
        if (!TryParseWeight(Cells[2], Weight))
            continue;

        const int32 VisemeId = FCString::Atoi(*Cells[0]);
        const FName MorphName(*Cells[1].TrimStartAndEnd());
        if (VisemeId < 0 || VisemeId > 21 || MorphName.IsNone())
            continue;

        FPromptMotionMorphWeight Entry;
        Entry.MorphName = MorphName;
        Entry.Weight = FMath::Clamp(Weight, -1.0f, 1.0f);
        Entry.FadeInSec = ParseOptionalFloat(Cells, 3, 0.05f, 0.0f, 1.0f);
        Entry.FadeOutSec = ParseOptionalFloat(Cells, 4, 0.08f, 0.0f, 1.0f);
        OutVisemes.FindOrAdd(VisemeId).Add(Entry);
    }

    return !OutVisemes.IsEmpty();
}
