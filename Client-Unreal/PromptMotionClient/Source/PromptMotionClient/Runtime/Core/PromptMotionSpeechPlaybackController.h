#pragma once

#include "CoreMinimal.h"
#include "PromptMotionTtsClient.h"
#include "Sound/SoundWaveProcedural.h"

class UAudioComponent;
struct FPromptMotionSpeechPlaybackSettings
{
    FString ServerUrl;
    bool bEnableTts = true;
    bool bEnableSentenceQueue = true;
};

struct FPromptMotionSpeechPlaybackEvents
{
    TFunction<void(const FString& RequestId)> OnTtsDisabled;
    TFunction<void(const FString& RequestId)> OnTtsRequestStarted;
    TFunction<void(const FString& RequestId)> OnTtsFailed;
    TFunction<void(const FString& RequestId, const FPromptMotionSpeechTimeline& Timeline)> OnTtsReady;
    TFunction<void(const FString& RequestId, const FPromptMotionSpeechTimeline& Timeline)> OnTimelineReady;
    TFunction<void(const FString& RequestId)> OnAudioStarted;
};

class FPromptMotionSpeechPlaybackController : public TSharedFromThis<FPromptMotionSpeechPlaybackController>
{
public:
    void Configure(UObject* InOwner, const FPromptMotionSpeechPlaybackSettings& InSettings, FPromptMotionSpeechPlaybackEvents InEvents);
    void Shutdown();

    void Start(const FString& LlmRequestId, const FString& ReplyText, const FString& TtsStyle);
    void StartTimeline(const FString& LlmRequestId, const FPromptMotionSpeechTimeline& Timeline);
    void UpdateTimeline(const FString& LlmRequestId, const FPromptMotionSpeechTimeline& Timeline);
    void Cancel();

    bool IsPlaybackActive() const;
    FString GetActiveRequestId() const { return ActiveRequestId; }

private:
    struct FSpeechSegment
    {
        int32 Index = 0;
        FString Text;
        FPromptMotionSpeechTimeline Timeline;
        TArray<uint8> WavBytes;
        bool bTtsReady = false;
        bool bAudioReady = false;
        bool bDownloadRequested = false;
        bool bFailed = false;
    };

    struct FWavParseResult
    {
        int32 SampleRate = 0;
        int32 NumChannels = 0;
        int32 BitsPerSample = 0;
        int32 DataOffset = 0;
        int32 DataSize = 0;
    };

    TWeakObjectPtr<UObject> Owner;
    FPromptMotionSpeechPlaybackSettings Settings;
    FPromptMotionSpeechPlaybackEvents Events;
    TUniquePtr<FPromptMotionTtsClient> TtsClient;
    FString CachedBaseUrl;
    FString ActiveRequestId;
    FString ActiveTtsStyle;
    FPromptMotionSpeechTimeline ActiveTimeline;
    TArray<FSpeechSegment> Segments;
    int32 CurrentSegmentIndex = INDEX_NONE;
    int32 NextSynthesizeIndex = 0;
    bool bSynthesisInFlight = false;
    bool bWaitingForNextSegment = false;
    bool bAudioStartedReported = false;
    bool bTtsReadyReported = false;
    TWeakObjectPtr<UAudioComponent> AudioComponent;
    TStrongObjectPtr<USoundWaveProcedural> ActiveSoundWave;

    void EnsureTtsClient();
    void StartNextSynthesis();
    void RequestSegmentAudio(int32 SegmentIndex);
    int32 FindSegmentByTimelineId(const FString& TimelineId) const;
    bool ShouldAutoPlaySegment(int32 SegmentIndex) const;
    void TryPlaySegment(int32 SegmentIndex);
    void PlayAudio(const FString& RequestId, int32 SegmentIndex);
    void HandleAudioFinished(const FString& RequestId, int32 SegmentIndex);
    void ClearAudioFinishTimer();
    static TArray<FString> SplitIntoSentences(const FString& Text);
    static bool TryParseWavHeader(const TArray<uint8>& WavBytes, FWavParseResult& Out);

    FTimerHandle AudioFinishFallbackTimer;
};
