#pragma once

#include "CoreMinimal.h"

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

private:

    /** emotion 문자열을 preset 키로 변환 */
    static FString EmotionToPresetKey(const FString& Emotion);

    /** preset 키 → base weight 맵 */
    static const TMap<FString, FPresetMap>& GetPresets();

    /** 모든 preset에 등장하는 morph 이름 → 0.0f (초기화 기준) */
    static const FPresetMap& GetFullResetMap();
};
