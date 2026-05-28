#pragma once

#include "CoreMinimal.h"
#include "PromptMotionTypes.h"

/**
 * PromptMotionLab TTS HTTP 클라이언트.
 * UObject 아님 — 순수 C++.
 *
 * 사용처: UPromptMotionRuntimeComponent가 소유.
 *
 * 흐름:
 *   1. Synthesize() — POST /api/runtime/tts/synthesize → SpeechTimeline 획득
 *   2. DownloadAudio() — GET /api/runtime/audio/{utteranceId}.wav → WAV 바이너리
 */
class FPromptMotionTtsClient
{
public:
    explicit FPromptMotionTtsClient(const FString& InBaseUrl);

    /**
     * 텍스트 → SpeechTimeline 합성 요청.
     * OnComplete: (bSuccess, SpeechTimeline)
     */
    void Synthesize(
        const FString& Text,
        const FString& TtsStyle,
        TFunction<void(bool bSuccess, const FPromptMotionSpeechTimeline& Timeline)> OnComplete);

    /**
     * SpeechTimeline.AudioUrl로 WAV 바이너리 다운로드.
     * RelativeUrl: "/api/runtime/audio/utt_xxx.wav" 형식. BaseUrl과 결합.
     * OnComplete: (bSuccess, WavBytes)
     */
    void DownloadAudio(
        const FString& RelativeUrl,
        TFunction<void(bool bSuccess, TArray<uint8> WavBytes)> OnComplete);

private:
    FString BaseUrl;

    void SynthesizeAttempt(
        const FString& Text,
        const FString& TtsStyle,
        int32 Attempt,
        TSharedRef<TFunction<void(bool, const FPromptMotionSpeechTimeline&)>> Callback);

    void DownloadAudioAttempt(
        const FString& RelativeUrl,
        int32 Attempt,
        TSharedRef<TFunction<void(bool, TArray<uint8>)>> Callback);

    static FPromptMotionSpeechTimeline ParseSpeechTimeline(const FString& JsonBody);
};
