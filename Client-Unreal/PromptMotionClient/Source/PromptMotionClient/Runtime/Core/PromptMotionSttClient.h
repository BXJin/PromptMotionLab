#pragma once

#include "CoreMinimal.h"

struct FPromptMotionSttResult
{
    FString Text;
    FString Language;
    FString Provider;
    FString Model;
    int32 SttLatencyMs = 0;
};

class FPromptMotionSttClient
{
public:
    explicit FPromptMotionSttClient(const FString& InBaseUrl);

    void TranscribeWav(
        const TArray<uint8>& WavBytes,
        const FString& Language,
        TFunction<void(bool bSuccess, const FPromptMotionSttResult& Result)> OnComplete);

private:
    FString BaseUrl;

    void TranscribeWavAttempt(
        const TArray<uint8>& WavBytes,
        const FString& Language,
        int32 Attempt,
        TSharedRef<TFunction<void(bool, const FPromptMotionSttResult&)>> Callback);

    static FPromptMotionSttResult ParseResult(const FString& JsonBody);
};
