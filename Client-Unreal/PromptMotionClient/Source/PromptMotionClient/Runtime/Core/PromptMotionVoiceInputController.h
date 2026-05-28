#pragma once

#include "CoreMinimal.h"
#include "PromptMotionLatencyLogger.h"
#include "PromptMotionStreamingSttClient.h"
#include "PromptMotionSttClient.h"

class IVoiceCapture;

struct FPromptMotionVoiceInputSettings
{
    FString ServerUrl;
    FString StreamingSttWebSocketUrl;
    FString Language = TEXT("ko");
    int32 SampleRate = 16000;
    float VadStartRmsThreshold = 0.035f;
    float VadEndRmsThreshold = 0.018f;
    float VadMinSpeechSeconds = 0.25f;
    float VadEndSilenceSeconds = 0.55f;
    float PollIntervalSeconds = 0.02f;
    bool bEnableVoiceInput = true;
    bool bEnableVoiceBargeIn = true;
    bool bEnableStreamingStt = false;
};

struct FPromptMotionVoiceInputEvents
{
    TFunction<bool()> IsVoiceBlocked;
    TFunction<bool()> IsPlaybackActive;
    TFunction<void()> OnBargeInRequested;
    TFunction<void()> OnSpeechStarted;
    TFunction<void()> OnTranscribing;
    TFunction<void()> OnError;
    TFunction<void(const FPromptMotionSttResult& Result, const FPromptMotionVoiceLatencyTrace& Trace)> OnTranscriptReady;
};

class FPromptMotionVoiceInputController : public TSharedFromThis<FPromptMotionVoiceInputController>
{
public:
    void Configure(const FPromptMotionVoiceInputSettings& InSettings, FPromptMotionVoiceInputEvents InEvents);
    void Shutdown();

    bool StartPushToTalk(double NowSeconds);
    bool StopPushToTalkAndSend(double NowSeconds);
    void SetVadEnabled(bool bEnabled, double NowSeconds);
    void Tick(double NowSeconds);

    bool IsPushToTalkActive() const { return bPushToTalkActive; }
    bool IsVadEnabled() const { return bVadEnabled; }
    bool IsVadSpeechActive() const { return bVadSpeechActive; }
    bool IsSttInFlight() const { return bSttInFlight; }

private:
    FPromptMotionVoiceInputSettings Settings;
    FPromptMotionVoiceInputEvents Events;

    TUniquePtr<FPromptMotionSttClient> SttClient;
    TUniquePtr<FPromptMotionStreamingSttClient> StreamingSttClient;
    FString CachedSttBaseUrl;
    FString CachedStreamingSttWebSocketUrl;
    TSharedPtr<IVoiceCapture> VoiceCapture;
    TArray<uint8> PcmBuffer;
    bool bPushToTalkActive = false;
    bool bVadEnabled = false;
    bool bVadSpeechActive = false;
    bool bCaptureStarted = false;
    bool bSttInFlight = false;
    bool bStreamingFinalReceived = false;
    double CaptureStartSeconds = 0.0;
    double VadSpeechStartSeconds = 0.0;
    double VadLastAboveThresholdSeconds = 0.0;
    double LastPollSeconds = -1000.0;
    FPromptMotionVoiceLatencyTrace PendingTrace;

    bool EnsureVoiceCapture();
    void EnsureSttClient();
    void EnsureStreamingSttClient();
    void BeginCaptureBuffer(double NowSeconds);
    void SubmitPcmToStt(double NowSeconds);
    void SubmitStreamingStt(double NowSeconds);
    bool ShouldAcceptSpeechStart() const;

    static float ComputePcm16Rms(const TArray<uint8>& PcmBytes, int32 StartByteIndex);
    static TArray<uint8> BuildPcm16MonoWav(const TArray<uint8>& PcmBytes, int32 SampleRate);
};
