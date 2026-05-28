#include "PromptMotionVoiceInputController.h"

#include "Interfaces/VoiceCapture.h"
#include "Modules/ModuleManager.h"
#include "PromptMotionLog.h"
#include "VoiceModule.h"

namespace
{
double ComputeElapsedMs(double StartSeconds, double EndSeconds)
{
    return StartSeconds > 0.0 && EndSeconds > 0.0
        ? (EndSeconds - StartSeconds) * 1000.0
        : -1.0;
}

void WriteU16(TArray<uint8>& Bytes, uint16 Value)
{
    Bytes.Add(static_cast<uint8>(Value & 0xff));
    Bytes.Add(static_cast<uint8>((Value >> 8) & 0xff));
}

void WriteU32(TArray<uint8>& Bytes, uint32 Value)
{
    Bytes.Add(static_cast<uint8>(Value & 0xff));
    Bytes.Add(static_cast<uint8>((Value >> 8) & 0xff));
    Bytes.Add(static_cast<uint8>((Value >> 16) & 0xff));
    Bytes.Add(static_cast<uint8>((Value >> 24) & 0xff));
}

void WriteAscii(TArray<uint8>& Bytes, const ANSICHAR* Text, int32 Count)
{
    for (int32 i = 0; i < Count; ++i)
        Bytes.Add(static_cast<uint8>(Text[i]));
}
}

void FPromptMotionVoiceInputController::Configure(
    const FPromptMotionVoiceInputSettings& InSettings,
    FPromptMotionVoiceInputEvents InEvents)
{
    Settings = InSettings;
    Events = MoveTemp(InEvents);
}

void FPromptMotionVoiceInputController::Shutdown()
{
    if (VoiceCapture.IsValid())
    {
        VoiceCapture->Stop();
        bCaptureStarted = false;
    }

    SttClient.Reset();
    StreamingSttClient.Reset();
    VoiceCapture.Reset();
    PcmBuffer.Reset();
    bPushToTalkActive = false;
    bVadEnabled = false;
    bVadSpeechActive = false;
    bSttInFlight = false;
    bStreamingFinalReceived = false;
}

bool FPromptMotionVoiceInputController::StartPushToTalk(double NowSeconds)
{
    if (bSttInFlight)
    {
        UE_LOG(LogPromptMotion, Log, TEXT("[STT] PTT ignored while STT request is in flight"));
        return false;
    }

    if (!Settings.bEnableVoiceInput || !EnsureVoiceCapture())
        return false;

    if (!ShouldAcceptSpeechStart())
        return false;

    bPushToTalkActive = true;
    bVadSpeechActive = false;
    BeginCaptureBuffer(NowSeconds);
    if (Settings.bEnableStreamingStt)
    {
        EnsureStreamingSttClient();
        if (StreamingSttClient.IsValid())
        {
            bStreamingFinalReceived = false;
            StreamingSttClient->Start(Settings.Language, Settings.SampleRate);
        }
    }
    PendingTrace = FPromptMotionVoiceLatencyTrace{};
    PendingTrace.InputMode = TEXT("ptt");
    PendingTrace.SpeechStartWorldSeconds = CaptureStartSeconds;
    if (Events.OnSpeechStarted)
        Events.OnSpeechStarted();
    return true;
}

bool FPromptMotionVoiceInputController::StopPushToTalkAndSend(double NowSeconds)
{
    if (!bPushToTalkActive)
        return false;

    bPushToTalkActive = false;
    if (VoiceCapture.IsValid() && !bVadEnabled)
    {
        VoiceCapture->Stop();
        bCaptureStarted = false;
    }

    PendingTrace.SpeechEndWorldSeconds = NowSeconds;
    UE_LOG(LogPromptMotion, Log, TEXT("[VoiceLatency] ptt_stop speechMs=%.0f streaming=%s"),
        ComputeElapsedMs(PendingTrace.SpeechStartWorldSeconds, PendingTrace.SpeechEndWorldSeconds),
        Settings.bEnableStreamingStt ? TEXT("true") : TEXT("false"));
    if (Settings.bEnableStreamingStt)
        SubmitStreamingStt(NowSeconds);
    else
        SubmitPcmToStt(NowSeconds);
    return true;
}

void FPromptMotionVoiceInputController::SetVadEnabled(bool bEnabled, double /*NowSeconds*/)
{
    bVadEnabled = bEnabled;
    bVadSpeechActive = false;
    PcmBuffer.Reset();

    if (bEnabled)
    {
        EnsureVoiceCapture();
        LastPollSeconds = -1000.0;
    }
    else if (!bPushToTalkActive && VoiceCapture.IsValid())
    {
        VoiceCapture->Stop();
        bCaptureStarted = false;
    }
}

void FPromptMotionVoiceInputController::Tick(double NowSeconds)
{
    if (!Settings.bEnableVoiceInput || (!bPushToTalkActive && !bVadEnabled) || !EnsureVoiceCapture())
        return;

    if (NowSeconds - LastPollSeconds < Settings.PollIntervalSeconds)
        return;
    LastPollSeconds = NowSeconds;

    uint32 AvailableBytes = 0;
    const EVoiceCaptureState::Type CaptureState = VoiceCapture->GetCaptureState(AvailableBytes);
    if (CaptureState != EVoiceCaptureState::Ok || AvailableBytes == 0)
        return;

    TArray<uint8> Chunk;
    Chunk.SetNumUninitialized(static_cast<int32>(AvailableBytes));
    uint32 ReadBytes = 0;
    VoiceCapture->GetVoiceData(Chunk.GetData(), AvailableBytes, ReadBytes);
    if (ReadBytes == 0)
        return;
    Chunk.SetNum(static_cast<int32>(ReadBytes));

    if (bPushToTalkActive)
    {
        if (Settings.bEnableStreamingStt && StreamingSttClient.IsValid())
            StreamingSttClient->SendAudioChunk(Chunk);
        else
            PcmBuffer.Append(Chunk);
        return;
    }

    const float ChunkRms = ComputePcm16Rms(Chunk, 0);
    if (!bVadSpeechActive)
    {
        if (ChunkRms < Settings.VadStartRmsThreshold)
            return;
        if (!ShouldAcceptSpeechStart())
            return;

        BeginCaptureBuffer(NowSeconds);
        bVadSpeechActive = true;
        VadSpeechStartSeconds = NowSeconds;
        VadLastAboveThresholdSeconds = NowSeconds;
        PendingTrace = FPromptMotionVoiceLatencyTrace{};
        PendingTrace.InputMode = TEXT("vad");
        PendingTrace.SpeechStartWorldSeconds = VadSpeechStartSeconds;
        if (Settings.bEnableStreamingStt)
        {
            EnsureStreamingSttClient();
            if (StreamingSttClient.IsValid())
            {
                bStreamingFinalReceived = false;
                StreamingSttClient->Start(Settings.Language, Settings.SampleRate);
            }
        }
        if (Events.OnSpeechStarted)
            Events.OnSpeechStarted();
        UE_LOG(LogPromptMotion, Log, TEXT("[STT] VAD speech start rms=%.3f"), ChunkRms);
    }

    if (Settings.bEnableStreamingStt && StreamingSttClient.IsValid())
        StreamingSttClient->SendAudioChunk(Chunk);
    else
        PcmBuffer.Append(Chunk);
    if (ChunkRms >= Settings.VadEndRmsThreshold)
        VadLastAboveThresholdSeconds = NowSeconds;

    const bool bLongEnough = (NowSeconds - VadSpeechStartSeconds) >= Settings.VadMinSpeechSeconds;
    const bool bSilenceLongEnough = (NowSeconds - VadLastAboveThresholdSeconds) >= Settings.VadEndSilenceSeconds;
    if (bLongEnough && bSilenceLongEnough)
    {
        bVadSpeechActive = false;
        PendingTrace.SpeechEndWorldSeconds = NowSeconds;
        UE_LOG(LogPromptMotion, Log, TEXT("[STT] VAD speech end pcmBytes=%d"), PcmBuffer.Num());
        if (Settings.bEnableStreamingStt)
            SubmitStreamingStt(NowSeconds);
        else
            SubmitPcmToStt(NowSeconds);
    }
}

bool FPromptMotionVoiceInputController::EnsureVoiceCapture()
{
    if (VoiceCapture.IsValid())
    {
        if (!bCaptureStarted)
        {
            VoiceCapture->Start();
            bCaptureStarted = true;
        }
        return true;
    }

    if (!FModuleManager::Get().IsModuleLoaded(TEXT("Voice")))
        FModuleManager::LoadModuleChecked<FVoiceModule>(TEXT("Voice"));

    VoiceCapture = FVoiceModule::Get().CreateVoiceCapture(TEXT(""), Settings.SampleRate, 1);
    if (!VoiceCapture.IsValid())
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[STT] Voice capture unavailable"));
        return false;
    }

    VoiceCapture->Start();
    bCaptureStarted = true;
    UE_LOG(LogPromptMotion, Log, TEXT("[STT] Voice capture started: %dHz mono PCM16"), Settings.SampleRate);
    return true;
}

void FPromptMotionVoiceInputController::EnsureSttClient()
{
    const FString Normalized = Settings.ServerUrl.TrimEnd();
    if (SttClient.IsValid() && CachedSttBaseUrl == Normalized)
        return;

    CachedSttBaseUrl = Normalized;
    SttClient = MakeUnique<FPromptMotionSttClient>(CachedSttBaseUrl);
}

void FPromptMotionVoiceInputController::EnsureStreamingSttClient()
{
    if (Settings.StreamingSttWebSocketUrl.IsEmpty())
        return;
    if (StreamingSttClient.IsValid() && CachedStreamingSttWebSocketUrl == Settings.StreamingSttWebSocketUrl)
        return;

    CachedStreamingSttWebSocketUrl = Settings.StreamingSttWebSocketUrl;
    StreamingSttClient = MakeUnique<FPromptMotionStreamingSttClient>(CachedStreamingSttWebSocketUrl);
    StreamingSttClient->OnStarted = []
    {
        UE_LOG(LogPromptMotion, Log, TEXT("[STT] Streaming session started"));
    };
    StreamingSttClient->OnPartial = [](const FString& Text)
    {
        UE_LOG(LogPromptMotion, Verbose, TEXT("[STT] Streaming partial: \"%s\""), *Text);
    };
    TWeakPtr<FPromptMotionVoiceInputController> WeakSelf = AsShared();
    StreamingSttClient->OnFinal = [WeakSelf](const FPromptMotionSttResult& Result)
    {
        TSharedPtr<FPromptMotionVoiceInputController> Self = WeakSelf.Pin();
        if (!Self.IsValid())
            return;

        FPromptMotionVoiceLatencyTrace Trace = Self->PendingTrace;
        Trace.SttReadyWorldSeconds = FPlatformTime::Seconds();
        Trace.Transcript = Result.Text;
        Trace.Provider = Result.Provider;
        Trace.Model = Result.Model;
        Trace.SttProviderLatencyMs = Result.SttLatencyMs;
        Self->bSttInFlight = false;
        Self->bStreamingFinalReceived = true;
        UE_LOG(LogPromptMotion, Log, TEXT("[STT] Streaming final: \"%s\" provider=%s/%s latency=%dms"),
            *Result.Text, *Result.Provider, *Result.Model, Result.SttLatencyMs);
        UE_LOG(LogPromptMotion, Log,
            TEXT("[VoiceLatency] stt_final mode=%s speechStartToFinalMs=%.0f speechEndToFinalMs=%.0f stopToFinalMs=%.0f providerLatencyMs=%d"),
            *Trace.InputMode,
            ComputeElapsedMs(Trace.SpeechStartWorldSeconds, Trace.SttReadyWorldSeconds),
            ComputeElapsedMs(Trace.SpeechEndWorldSeconds, Trace.SttReadyWorldSeconds),
            ComputeElapsedMs(Trace.SttRequestSentWorldSeconds, Trace.SttReadyWorldSeconds),
            Trace.SttProviderLatencyMs);
        if (Self->Events.OnTranscriptReady)
            Self->Events.OnTranscriptReady(Result, Trace);
    };
    StreamingSttClient->OnError = [WeakSelf](const FString& Error)
    {
        TSharedPtr<FPromptMotionVoiceInputController> Self = WeakSelf.Pin();
        if (!Self.IsValid())
            return;
        if (Self->bStreamingFinalReceived)
        {
            UE_LOG(LogPromptMotion, Verbose, TEXT("[STT] Streaming post-final error ignored: %s"), *Error);
            return;
        }
        Self->bSttInFlight = false;
        UE_LOG(LogPromptMotion, Warning, TEXT("[STT] Streaming error: %s"), *Error);
        if (Self->Events.OnError)
            Self->Events.OnError();
    };
    StreamingSttClient->OnClosed = [WeakSelf]()
    {
        TSharedPtr<FPromptMotionVoiceInputController> Self = WeakSelf.Pin();
        if (!Self.IsValid())
            return;

        const bool bWasInFlight = Self->bSttInFlight;
        Self->bSttInFlight = false;
        if (bWasInFlight && !Self->bStreamingFinalReceived && Self->Events.OnError)
            Self->Events.OnError();
    };
}

void FPromptMotionVoiceInputController::BeginCaptureBuffer(double NowSeconds)
{
    PcmBuffer.Reset();
    CaptureStartSeconds = NowSeconds;
    if (VoiceCapture.IsValid())
    {
        VoiceCapture->Start();
        bCaptureStarted = true;
    }
}

void FPromptMotionVoiceInputController::SubmitPcmToStt(double NowSeconds)
{
    if (bSttInFlight)
    {
        UE_LOG(LogPromptMotion, Log, TEXT("[STT] Submit ignored while STT request is in flight"));
        PcmBuffer.Reset();
        return;
    }

    const int32 MinBytes = FMath::Max(1, Settings.SampleRate * 2 / 10);
    if (PcmBuffer.Num() < MinBytes)
    {
        UE_LOG(LogPromptMotion, Verbose, TEXT("[STT] Voice buffer too short: %d bytes"), PcmBuffer.Num());
        PcmBuffer.Reset();
        return;
    }

    EnsureSttClient();
    PendingTrace.SttRequestSentWorldSeconds = NowSeconds;
    UE_LOG(LogPromptMotion, Log, TEXT("[VoiceLatency] stt_request_sent mode=%s speechEndToSttSendMs=%.0f pcmBytes=%d"),
        *PendingTrace.InputMode,
        ComputeElapsedMs(PendingTrace.SpeechEndWorldSeconds, PendingTrace.SttRequestSentWorldSeconds),
        PcmBuffer.Num());
    FPromptMotionVoiceLatencyTrace CapturedTrace = PendingTrace;
    const TArray<uint8> WavBytes = BuildPcm16MonoWav(PcmBuffer, Settings.SampleRate);
    PcmBuffer.Reset();
    bSttInFlight = true;
    if (Events.OnTranscribing)
        Events.OnTranscribing();

    TWeakPtr<FPromptMotionVoiceInputController> WeakSelf = AsShared();
    SttClient->TranscribeWav(WavBytes, Settings.Language,
        [WeakSelf, Trace = MoveTemp(CapturedTrace)](bool bSuccess, const FPromptMotionSttResult& Result) mutable
        {
            TSharedPtr<FPromptMotionVoiceInputController> Self = WeakSelf.Pin();
            if (!Self.IsValid())
                return;

            if (!bSuccess || Result.Text.IsEmpty())
            {
                Self->bSttInFlight = false;
                UE_LOG(LogPromptMotion, Warning, TEXT("[STT] Transcribe failed or empty"));
                if (Self->Events.OnError)
                    Self->Events.OnError();
                return;
            }

            UE_LOG(LogPromptMotion, Log, TEXT("[STT] Transcribed: \"%s\" provider=%s/%s latency=%dms"),
                *Result.Text, *Result.Provider, *Result.Model, Result.SttLatencyMs);
            Trace.SttReadyWorldSeconds = FPlatformTime::Seconds();
            Trace.Transcript = Result.Text;
            Trace.Provider = Result.Provider;
            Trace.Model = Result.Model;
            Trace.SttProviderLatencyMs = Result.SttLatencyMs;
            Self->bSttInFlight = false;
            UE_LOG(LogPromptMotion, Log,
                TEXT("[VoiceLatency] stt_final mode=%s speechStartToFinalMs=%.0f speechEndToFinalMs=%.0f stopToFinalMs=%.0f providerLatencyMs=%d"),
                *Trace.InputMode,
                ComputeElapsedMs(Trace.SpeechStartWorldSeconds, Trace.SttReadyWorldSeconds),
                ComputeElapsedMs(Trace.SpeechEndWorldSeconds, Trace.SttReadyWorldSeconds),
                ComputeElapsedMs(Trace.SttRequestSentWorldSeconds, Trace.SttReadyWorldSeconds),
                Trace.SttProviderLatencyMs);
            if (Self->Events.OnTranscriptReady)
                Self->Events.OnTranscriptReady(Result, Trace);
        });
}

void FPromptMotionVoiceInputController::SubmitStreamingStt(double NowSeconds)
{
    EnsureStreamingSttClient();
    if (!StreamingSttClient.IsValid() || !StreamingSttClient->IsConnected())
    {
        bSttInFlight = false;
        if (Events.OnError)
            Events.OnError();
        return;
    }

    PendingTrace.SttRequestSentWorldSeconds = NowSeconds;
    UE_LOG(LogPromptMotion, Log, TEXT("[VoiceLatency] stt_stop_sent mode=%s speechEndToStopMs=%.0f"),
        *PendingTrace.InputMode,
        ComputeElapsedMs(PendingTrace.SpeechEndWorldSeconds, PendingTrace.SttRequestSentWorldSeconds));
    bSttInFlight = true;
    PcmBuffer.Reset();
    if (Events.OnTranscribing)
        Events.OnTranscribing();
    StreamingSttClient->Stop();
}

bool FPromptMotionVoiceInputController::ShouldAcceptSpeechStart() const
{
    const bool bBlocked = Events.IsVoiceBlocked && Events.IsVoiceBlocked();
    if (!bBlocked)
        return true;

    const bool bPlaybackActive = Events.IsPlaybackActive && Events.IsPlaybackActive();
    if (Settings.bEnableVoiceBargeIn && bPlaybackActive)
    {
        if (Events.OnBargeInRequested)
            Events.OnBargeInRequested();
        return true;
    }
    return false;
}

float FPromptMotionVoiceInputController::ComputePcm16Rms(const TArray<uint8>& PcmBytes, int32 StartByteIndex)
{
    const int32 Start = FMath::Max(0, StartByteIndex) & ~1;
    const int32 SampleCount = (PcmBytes.Num() - Start) / 2;
    if (SampleCount <= 0)
        return 0.0f;

    double SumSquares = 0.0;
    const uint8* Data = PcmBytes.GetData() + Start;
    for (int32 i = 0; i < SampleCount; ++i)
    {
        const int16 Sample = static_cast<int16>(Data[i * 2] | (Data[i * 2 + 1] << 8));
        const double Normalized = static_cast<double>(Sample) / 32768.0;
        SumSquares += Normalized * Normalized;
    }
    return static_cast<float>(FMath::Sqrt(SumSquares / SampleCount));
}

TArray<uint8> FPromptMotionVoiceInputController::BuildPcm16MonoWav(const TArray<uint8>& PcmBytes, int32 SampleRate)
{
    TArray<uint8> Wav;
    const uint32 DataBytes = static_cast<uint32>(PcmBytes.Num());
    const uint16 Channels = 1;
    const uint16 BitsPerSample = 16;
    const uint32 ByteRate = static_cast<uint32>(SampleRate) * Channels * (BitsPerSample / 8);
    const uint16 BlockAlign = Channels * (BitsPerSample / 8);

    Wav.Reserve(44 + PcmBytes.Num());
    WriteAscii(Wav, "RIFF", 4);
    WriteU32(Wav, 36 + DataBytes);
    WriteAscii(Wav, "WAVE", 4);
    WriteAscii(Wav, "fmt ", 4);
    WriteU32(Wav, 16);
    WriteU16(Wav, 1);
    WriteU16(Wav, Channels);
    WriteU32(Wav, static_cast<uint32>(SampleRate));
    WriteU32(Wav, ByteRate);
    WriteU16(Wav, BlockAlign);
    WriteU16(Wav, BitsPerSample);
    WriteAscii(Wav, "data", 4);
    WriteU32(Wav, DataBytes);
    Wav.Append(PcmBytes);
    return Wav;
}
