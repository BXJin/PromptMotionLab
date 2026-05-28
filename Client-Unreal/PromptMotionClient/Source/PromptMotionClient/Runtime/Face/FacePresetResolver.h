#pragma once

#include "CoreMinimal.h"
#include "PromptMotionFaceConfig.h"

/**
 * emotion + intensity → morph target weight map 변환기.
 * 순수 C++ - UObject 아님.
 *
 * 동작 원리:
 *   emotion 문자열을 preset 키로 매핑한 뒤,
 *   각 morph 기본 weight에 intensity를 곱해 반환.
 *   이전 preset에서 사용된 morph도 0으로 포함 → 잔류 표정 제거.
 *
 * 공식: FinalWeight = PresetBaseWeight * Intensity
 */
class FFacePresetResolver
{
public:
    using FPresetMap = TMap<FName, float>;

    /**
     * emotion + intensity를 morph target 적용값으로 변환.
     * 반환 맵에는 이전 preset 초기화용 zero-weight morph도 포함됨.
     */
    static TMap<FName, float> Resolve(const FString& Emotion, float Intensity);
    static TMap<FName, float> Resolve(const FString& Emotion, float Intensity, const FString& CharacterId);
    static TMap<FName, FPromptMotionFaceMorphSetting> ResolveSettings(const FString& Emotion, float Intensity, const FString& CharacterId);

    /**
     * CharacterId에 해당하는 CSV를 로드해 내부 캐시에 저장.
     * BeginPlay / ReloadFaceConfig / SetConversationMode 시 호출.
     * 같은 CharacterId 재호출 시 재로드(핫리로드 지원).
     */
    static void LoadCsvForCharacter(const FString& CharacterId);

    /**
     * 현재 캐시(CSV 우선, fallback 하드코딩)에서 preset + morph의 저장된 weight 반환.
     * 없으면 0.0f. Debug UI에서 콤보박스 선택 변경 시 슬라이더 초기값 세팅용.
     */
    static float QueryWeight(const FString& Preset, FName MorphName, const FString& CharacterId = TEXT(""));
    static FPromptMotionFaceMorphSetting QuerySetting(const FString& Preset, FName MorphName, const FString& CharacterId = TEXT(""));

private:

    /** emotion 문자열을 preset 키로 변환 */
    static FString EmotionToPresetKey(const FString& Emotion);

    /** preset 키 → base weight 맵 (하드코딩 fallback) */
    static const TMap<FString, FPresetMap>& GetPresets();

    /** 모든 preset에 등장하는 morph 이름 → 0.0f (초기화 기준) */
    static const FPresetMap& GetFullResetMap();
    static FPresetMap BuildFullResetMap(const TMap<FString, FPresetMap>& Presets);
};
