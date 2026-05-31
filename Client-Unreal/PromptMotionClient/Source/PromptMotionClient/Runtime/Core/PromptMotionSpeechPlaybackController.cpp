#include "PromptMotionSpeechPlaybackController.h"

#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "PromptMotionLog.h"
#include "Sound/SoundWaveProcedural.h"
#include "TimerManager.h"

void FPromptMotionSpeechPlaybackController::Configure(
    UObject* InOwner,
    const FPromptMotionSpeechPlaybackSettings& InSettings,
    FPromptMotionSpeechPlaybackEvents InEvents)
{
    Owner = InOwner;
    Settings = InSettings;
    Events = MoveTemp(InEvents);
}

void FPromptMotionSpeechPlaybackController::Shutdown()
{
    Cancel();
    TtsClient.Reset();
}

void FPromptMotionSpeechPlaybackController::Start(
    const FString& LlmRequestId,
    const FString& ReplyText,
    const FString& TtsStyle)
{
    if (!Settings.bEnableTts || ReplyText.IsEmpty())
    {
        if (Events.OnTtsDisabled)
            Events.OnTtsDisabled(LlmRequestId);
        return;
    }

    Cancel();
    ActiveRequestId = LlmRequestId;
    ActiveTtsStyle = TtsStyle;
    EnsureTtsClient();
    if (Events.OnTtsRequestStarted)
        Events.OnTtsRequestStarted(LlmRequestId);

    const TArray<FString> SentenceTexts = Settings.bEnableSentenceQueue
        ? SplitIntoSentences(ReplyText)
        : TArray<FString>{ReplyText};
    Segments.Reset();
    Segments.Reserve(SentenceTexts.Num());
    for (int32 Index = 0; Index < SentenceTexts.Num(); ++Index)
    {
        FSpeechSegment Segment;
        Segment.Index = Index;
        Segment.Text = SentenceTexts[Index];
        Segments.Add(MoveTemp(Segment));
    }

    NextSynthesizeIndex = 0;
    StartNextSynthesis();
}

void FPromptMotionSpeechPlaybackController::StartTimeline(
    const FString& LlmRequestId,
    const FPromptMotionSpeechTimeline& Timeline)
{
    Cancel();
    UpdateTimeline(LlmRequestId, Timeline);
}

void FPromptMotionSpeechPlaybackController::UpdateTimeline(
    const FString& LlmRequestId,
    const FPromptMotionSpeechTimeline& Timeline)
{
    if (!Settings.bEnableTts || Timeline.UtteranceId.IsEmpty())
    {
        if (Events.OnTtsDisabled)
            Events.OnTtsDisabled(LlmRequestId);
        return;
    }

    const bool bNewRequest = ActiveRequestId != LlmRequestId;
    if (bNewRequest)
    {
        Cancel();
        ActiveRequestId = LlmRequestId;
        if (Events.OnTtsRequestStarted)
            Events.OnTtsRequestStarted(LlmRequestId);
    }

    ActiveTimeline = Timeline;
    EnsureTtsClient();
    if (!bTtsReadyReported && Events.OnTtsReady)
    {
        Events.OnTtsReady(LlmRequestId, Timeline);
        bTtsReadyReported = true;
    }

    if (Timeline.Segments.Num() > 0)
    {
        for (const FPromptMotionSpeechSegment& SourceSegment : Timeline.Segments)
        {
            const FString SegmentTimelineId = SourceSegment.SegmentId.IsEmpty()
                ? FString::Printf(TEXT("%s_seg_%d"), *Timeline.UtteranceId, SourceSegment.Index)
                : SourceSegment.SegmentId;
            if (FindSegmentByTimelineId(SegmentTimelineId) != INDEX_NONE)
                continue;

            FSpeechSegment Segment;
            Segment.Index = SourceSegment.Index;
            Segment.Text = SourceSegment.Text;
            Segment.Timeline.UtteranceId = SegmentTimelineId;
            Segment.Timeline.Audio = SourceSegment.Audio;
            Segment.Timeline.AudioUrl = SourceSegment.Audio.Url;
            Segment.Timeline.DurationSeconds = SourceSegment.DurationSeconds > 0.0f
                ? SourceSegment.DurationSeconds
                : SourceSegment.Audio.DurationSeconds;
            Segment.Timeline.Visemes = SourceSegment.Visemes;
            Segment.Timeline.Provider = Timeline.Provider;
            Segment.Timeline.Model = Timeline.Model;
            Segment.Timeline.TtsLatencyMs = SourceSegment.TtsLatencyMs;
            const int32 NewSegmentIndex = Segments.Add(MoveTemp(Segment));
            UE_LOG(LogPromptMotion, Log, TEXT("[TTS] Async turn segment appended: request=%s segment=%d/%d id=%s"),
                *LlmRequestId, NewSegmentIndex + 1, Timeline.Segments.Num(), *SegmentTimelineId);
            RequestSegmentAudio(NewSegmentIndex);
        }
    }
    else if (Segments.Num() == 0)
    {
        FSpeechSegment Segment;
        Segment.Index = 0;
        Segment.Timeline = Timeline;
        const int32 NewSegmentIndex = Segments.Add(MoveTemp(Segment));
        RequestSegmentAudio(NewSegmentIndex);
    }
}

void FPromptMotionSpeechPlaybackController::RequestSegmentAudio(int32 SegmentIndex)
{
    if (!Segments.IsValidIndex(SegmentIndex))
        return;

    if (!TtsClient.IsValid())
    {
        if (Events.OnTtsFailed)
            Events.OnTtsFailed(ActiveRequestId);
        return;
    }

    FSpeechSegment& Segment = Segments[SegmentIndex];
    if (Segment.bDownloadRequested || Segment.bAudioReady || Segment.bFailed)
        return;

    const FString RequestId = ActiveRequestId;
    const FString AudioUrl = Segment.Timeline.AudioUrl;
    if (AudioUrl.IsEmpty())
    {
        Segment.bFailed = true;
        return;
    }

    Segment.bDownloadRequested = true;
    TWeakPtr<FPromptMotionSpeechPlaybackController> WeakSelf = AsShared();
    TtsClient->DownloadAudio(AudioUrl,
        [WeakSelf, RequestId, SegmentIndex](bool bDownloadOk, TArray<uint8> WavBytes)
        {
            TSharedPtr<FPromptMotionSpeechPlaybackController> Self = WeakSelf.Pin();
            if (!Self.IsValid() || Self->ActiveRequestId != RequestId || !Self->Segments.IsValidIndex(SegmentIndex))
                return;

            FSpeechSegment& DownloadSegment = Self->Segments[SegmentIndex];
            if (!bDownloadOk || WavBytes.IsEmpty())
            {
                DownloadSegment.bFailed = true;
                UE_LOG(LogPromptMotion, Warning, TEXT("[TTS] Async turn WAV download failed: segment=%d url=%s"),
                    SegmentIndex, *DownloadSegment.Timeline.AudioUrl);
                if (SegmentIndex == 0 && Self->Events.OnTtsFailed)
                    Self->Events.OnTtsFailed(RequestId);
            if (Self->bWaitingForNextSegment && SegmentIndex == Self->CurrentSegmentIndex + 1)
                Self->TryPlaySegment(SegmentIndex);
            return;
        }

            DownloadSegment.WavBytes = MoveTemp(WavBytes);
            DownloadSegment.bTtsReady = true;
            DownloadSegment.bAudioReady = true;
            UE_LOG(LogPromptMotion, Log, TEXT("[TTS] Async turn WAV ready: segment=%d bytes=%d"),
                SegmentIndex, DownloadSegment.WavBytes.Num());

            if (Self->ShouldAutoPlaySegment(SegmentIndex))
                Self->TryPlaySegment(SegmentIndex);
        });
}

void FPromptMotionSpeechPlaybackController::Cancel()
{
    ClearAudioFinishTimer();

    if (AudioComponent.IsValid())
        AudioComponent->Stop();

    AudioComponent.Reset();
    ActiveSoundWave.Reset();
    ActiveTimeline = FPromptMotionSpeechTimeline{};
    ActiveRequestId.Empty();
    ActiveTtsStyle.Empty();
    Segments.Reset();
    CurrentSegmentIndex = INDEX_NONE;
    NextSynthesizeIndex = 0;
    bSynthesisInFlight = false;
    bWaitingForNextSegment = false;
    bAudioStartedReported = false;
    bTtsReadyReported = false;
}

bool FPromptMotionSpeechPlaybackController::IsPlaybackActive() const
{
    return AudioComponent.IsValid() && AudioComponent->IsPlaying();
}

void FPromptMotionSpeechPlaybackController::EnsureTtsClient()
{
    const FString Normalized = Settings.ServerUrl.TrimEnd();
    if (TtsClient.IsValid() && CachedBaseUrl == Normalized)
        return;

    CachedBaseUrl = Normalized;
    TtsClient = MakeUnique<FPromptMotionTtsClient>(CachedBaseUrl);
}

void FPromptMotionSpeechPlaybackController::StartNextSynthesis()
{
    if (bSynthesisInFlight || !TtsClient.IsValid() || !Segments.IsValidIndex(NextSynthesizeIndex))
        return;

    const FString RequestId = ActiveRequestId;
    const int32 SegmentIndex = NextSynthesizeIndex++;
    bSynthesisInFlight = true;

    TWeakPtr<FPromptMotionSpeechPlaybackController> WeakSelf = AsShared();
    TtsClient->Synthesize(Segments[SegmentIndex].Text, ActiveTtsStyle,
        [WeakSelf, RequestId, SegmentIndex](bool bSuccess, const FPromptMotionSpeechTimeline& Timeline)
        {
            TSharedPtr<FPromptMotionSpeechPlaybackController> Self = WeakSelf.Pin();
            if (!Self.IsValid() || Self->ActiveRequestId != RequestId || !Self->Segments.IsValidIndex(SegmentIndex))
                return;

            Self->bSynthesisInFlight = false;
            FSpeechSegment& Segment = Self->Segments[SegmentIndex];
            if (!bSuccess)
            {
                Segment.bFailed = true;
                UE_LOG(LogPromptMotion, Warning, TEXT("[TTS] Synthesize failed for request %s segment=%d"), *RequestId, SegmentIndex);
                if (SegmentIndex == 0 && Self->Events.OnTtsFailed)
                    Self->Events.OnTtsFailed(RequestId);
                Self->StartNextSynthesis();
                return;
            }

            Segment.Timeline = Timeline;
            Segment.bTtsReady = true;
            if (SegmentIndex == 0 && Self->Events.OnTtsReady)
                Self->Events.OnTtsReady(RequestId, Timeline);

            UE_LOG(LogPromptMotion, Log, TEXT("[TTS] Segment synth OK: %s segment=%d/%d %.2fs visemes=%d"),
                *Timeline.UtteranceId, SegmentIndex + 1, Self->Segments.Num(), Timeline.DurationSeconds, Timeline.Visemes.Num());

            Self->TtsClient->DownloadAudio(Timeline.AudioUrl,
                [WeakSelf, RequestId, SegmentIndex](bool bDownloadOk, TArray<uint8> WavBytes)
                {
                    TSharedPtr<FPromptMotionSpeechPlaybackController> DownloadSelf = WeakSelf.Pin();
                    if (!DownloadSelf.IsValid() || DownloadSelf->ActiveRequestId != RequestId || !DownloadSelf->Segments.IsValidIndex(SegmentIndex))
                        return;

                    FSpeechSegment& DownloadSegment = DownloadSelf->Segments[SegmentIndex];
                    if (!bDownloadOk || WavBytes.IsEmpty())
                    {
                        DownloadSegment.bFailed = true;
                        UE_LOG(LogPromptMotion, Warning, TEXT("[TTS] WAV download failed for %s segment=%d"),
                            *DownloadSegment.Timeline.UtteranceId, SegmentIndex);
                        if (SegmentIndex == 0 && DownloadSelf->Events.OnTtsFailed)
                            DownloadSelf->Events.OnTtsFailed(RequestId);
                    if (DownloadSelf->bWaitingForNextSegment && SegmentIndex == DownloadSelf->CurrentSegmentIndex + 1)
                        DownloadSelf->TryPlaySegment(SegmentIndex);
                    return;
                }

                    DownloadSegment.WavBytes = MoveTemp(WavBytes);
                    DownloadSegment.bAudioReady = true;
                    UE_LOG(LogPromptMotion, Log, TEXT("[TTS] Segment WAV ready: segment=%d bytes=%d"),
                        SegmentIndex, DownloadSegment.WavBytes.Num());

                    if (DownloadSelf->ShouldAutoPlaySegment(SegmentIndex))
                        DownloadSelf->TryPlaySegment(SegmentIndex);
                });

            Self->StartNextSynthesis();
        });
}

int32 FPromptMotionSpeechPlaybackController::FindSegmentByTimelineId(const FString& TimelineId) const
{
    for (int32 Index = 0; Index < Segments.Num(); ++Index)
    {
        if (Segments[Index].Timeline.UtteranceId == TimelineId)
            return Index;
    }
    return INDEX_NONE;
}

bool FPromptMotionSpeechPlaybackController::ShouldAutoPlaySegment(int32 SegmentIndex) const
{
    if (SegmentIndex == 0)
        return true;
    if (bWaitingForNextSegment && SegmentIndex == CurrentSegmentIndex + 1)
        return true;
    return CurrentSegmentIndex == INDEX_NONE
        && (!AudioComponent.IsValid() || !AudioComponent->IsPlaying());
}

void FPromptMotionSpeechPlaybackController::TryPlaySegment(int32 SegmentIndex)
{
    if (!Segments.IsValidIndex(SegmentIndex) || ActiveRequestId.IsEmpty())
        return;
    if (Segments[SegmentIndex].bFailed)
    {
        TryPlaySegment(SegmentIndex + 1);
        return;
    }
    if (AudioComponent.IsValid() && AudioComponent->IsPlaying())
        return;
    if (!Segments[SegmentIndex].bAudioReady)
    {
        bWaitingForNextSegment = true;
        return;
    }

    bWaitingForNextSegment = false;
    PlayAudio(ActiveRequestId, SegmentIndex);
}

void FPromptMotionSpeechPlaybackController::PlayAudio(const FString& RequestId, int32 SegmentIndex)
{
    if (!Segments.IsValidIndex(SegmentIndex))
        return;

    UE_LOG(LogPromptMotion, Log, TEXT("[TTS] SegmentGap - PlayAudio entry seg=%d playAudioEntrySec=%.4f"),
        SegmentIndex, FPlatformTime::Seconds());

    FSpeechSegment& Segment = Segments[SegmentIndex];
    FWavParseResult WavInfo;
    if (!TryParseWavHeader(Segment.WavBytes, WavInfo))
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[TTS] WAV header parse failed (%d bytes)"), Segment.WavBytes.Num());
        return;
    }

    const float ComputedDuration = (WavInfo.SampleRate > 0 && WavInfo.NumChannels > 0 && WavInfo.BitsPerSample > 0)
        ? static_cast<float>(WavInfo.DataSize) / (WavInfo.SampleRate * WavInfo.NumChannels * (WavInfo.BitsPerSample / 8))
        : Segment.Timeline.DurationSeconds;

    if (WavInfo.BitsPerSample != 16)
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[TTS] Unsupported WAV bit depth: %d"), WavInfo.BitsPerSample);
        return;
    }

    UObject* OwnerObject = Owner.Get();
    if (!OwnerObject)
        return;

    USoundWaveProcedural* ProcWave = NewObject<USoundWaveProcedural>(OwnerObject);
    ProcWave->SetSampleRate(WavInfo.SampleRate);
    ProcWave->NumChannels = WavInfo.NumChannels;
    ProcWave->Duration = ComputedDuration;
    ProcWave->bLooping = false;
    ProcWave->SampleByteSize = WavInfo.BitsPerSample / 8;
    ProcWave->QueueAudio(Segment.WavBytes.GetData() + WavInfo.DataOffset, WavInfo.DataSize);
    ActiveSoundWave.Reset(ProcWave);

    if (AudioComponent.IsValid())
        AudioComponent->Stop();

    const double SpawnStartSec = FPlatformTime::Seconds();
    AudioComponent = UGameplayStatics::SpawnSound2D(
        OwnerObject,
        ProcWave,
        1.0f,
        1.0f,
        0.0f,
        nullptr,
        false,
        true); // bAutoDestroy=true: component self-destructs on finish → OnAudioFinishedNative fires reliably
    const double SpawnEndSec = FPlatformTime::Seconds();

    if (!AudioComponent.IsValid())
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[TTS] SpawnSound2D failed"));
        return;
    }

    CurrentSegmentIndex = SegmentIndex;
    ActiveTimeline = Segment.Timeline;

    if (!Segment.Timeline.Visemes.IsEmpty())
    {
        FString VisemeSequence;
        for (int32 Index = 0; Index < Segment.Timeline.Visemes.Num(); ++Index)
        {
            const FPromptMotionVisemeEvent& Event = Segment.Timeline.Visemes[Index];
            if (!VisemeSequence.IsEmpty())
                VisemeSequence += TEXT(", ");
            VisemeSequence += FString::Printf(TEXT("%.3fs:id%d/w%.2f"), Event.TimeSeconds, Event.VisemeId, Event.Weight);
        }

        UE_LOG(LogPromptMotion, Log, TEXT("[TTS] Viseme debug - segment=%d/%d text=\"%s\" duration=%.2fs visemes=[%s]"),
            SegmentIndex + 1,
            Segments.Num(),
            *Segment.Text,
            Segment.Timeline.DurationSeconds,
            *VisemeSequence);
    }

    if (Events.OnTimelineReady)
        Events.OnTimelineReady(RequestId, Segment.Timeline);
    if (!bAudioStartedReported && Events.OnAudioStarted)
    {
        Events.OnAudioStarted(RequestId);
        bAudioStartedReported = true;
    }

    TWeakPtr<FPromptMotionSpeechPlaybackController> WeakSelf = AsShared();
    AudioComponent->OnAudioFinishedNative.AddLambda(
        [WeakSelf, RequestId, SegmentIndex](UAudioComponent*)
        {
            TSharedPtr<FPromptMotionSpeechPlaybackController> Self = WeakSelf.Pin();
            if (Self.IsValid())
                Self->HandleAudioFinished(RequestId, SegmentIndex);
        });

    ClearAudioFinishTimer();
    if (UWorld* World = OwnerObject->GetWorld())
    {
        const float FinishDelaySeconds = FMath::Max(ComputedDuration + 0.10f, 0.10f);
        World->GetTimerManager().SetTimer(
            AudioFinishFallbackTimer,
            [WeakSelf, RequestId, SegmentIndex]()
            {
                TSharedPtr<FPromptMotionSpeechPlaybackController> Self = WeakSelf.Pin();
                if (Self.IsValid())
                {
                    UE_LOG(LogPromptMotion, Verbose, TEXT("[TTS] Audio finish fallback timer fired: request=%s segment=%d"),
                        *RequestId, SegmentIndex);
                    Self->HandleAudioFinished(RequestId, SegmentIndex);
                }
            },
            FinishDelaySeconds,
            false);
    }

    UE_LOG(LogPromptMotion, Log, TEXT("[TTS] Audio playing - segment=%d/%d %dHz %dch %dbit %.2fs queued=%d playing=%s spawnMs=%.1f"),
        SegmentIndex + 1,
        Segments.Num(),
        WavInfo.SampleRate,
        WavInfo.NumChannels,
        WavInfo.BitsPerSample,
        ComputedDuration,
        ProcWave->GetAvailableAudioByteCount(),
        AudioComponent->IsPlaying() ? TEXT("true") : TEXT("false"),
        (SpawnEndSec - SpawnStartSec) * 1000.0);
}

void FPromptMotionSpeechPlaybackController::HandleAudioFinished(const FString& RequestId, int32 SegmentIndex)
{
    if (ActiveRequestId != RequestId || SegmentIndex != CurrentSegmentIndex)
        return;

    const double FinishedAtSec = FPlatformTime::Seconds();
    ClearAudioFinishTimer();

    // bAutoDestroy=true: component already self-destructing — no explicit Stop() needed.
    // Clearing the pointer first ensures TryPlaySegment's IsValid()/IsPlaying() check passes cleanly.
    ActiveSoundWave.Reset();
    AudioComponent.Reset();
    CurrentSegmentIndex = INDEX_NONE;

    const int32 NextIndex = SegmentIndex + 1;
    if (Segments.IsValidIndex(NextIndex))
    {
        UE_LOG(LogPromptMotion, Log, TEXT("[TTS] SegmentGap - seg%d finished, calling TryPlaySegment(%d) gapStartSec=%.4f"),
            SegmentIndex, NextIndex, FinishedAtSec);
        TryPlaySegment(NextIndex);
    }
    else
    {
        UE_LOG(LogPromptMotion, Log, TEXT("[TTS] SegmentGap - seg%d finished (last segment) finishedAtSec=%.4f"),
            SegmentIndex, FinishedAtSec);
    }
}

void FPromptMotionSpeechPlaybackController::ClearAudioFinishTimer()
{
    if (UObject* OwnerObject = Owner.Get())
    {
        if (UWorld* World = OwnerObject->GetWorld())
            World->GetTimerManager().ClearTimer(AudioFinishFallbackTimer);
    }
}

TArray<FString> FPromptMotionSpeechPlaybackController::SplitIntoSentences(const FString& Text)
{
    TArray<FString> Result;
    FString Current;
    for (int32 Index = 0; Index < Text.Len(); ++Index)
    {
        const TCHAR Ch = Text[Index];
        Current.AppendChar(Ch);
        const bool bBoundary = Ch == TEXT('.') || Ch == TEXT('!') || Ch == TEXT('?') || Ch == TEXT('\n');
        if (bBoundary)
        {
            FString Trimmed = Current.TrimStartAndEnd();
            if (!Trimmed.IsEmpty())
                Result.Add(Trimmed);
            Current.Reset();
        }
    }

    FString Tail = Current.TrimStartAndEnd();
    if (!Tail.IsEmpty())
        Result.Add(Tail);
    if (Result.IsEmpty() && !Text.TrimStartAndEnd().IsEmpty())
        Result.Add(Text.TrimStartAndEnd());
    return Result;
}

bool FPromptMotionSpeechPlaybackController::TryParseWavHeader(const TArray<uint8>& WavBytes, FWavParseResult& Out)
{
    if (WavBytes.Num() < 44)
        return false;

    const uint8* D = WavBytes.GetData();
    if (FMemory::Memcmp(D, "RIFF", 4) != 0) return false;
    if (FMemory::Memcmp(D + 8, "WAVE", 4) != 0) return false;

    int32 Offset = 12;
    bool bFoundFmt = false;
    while (Offset + 8 <= WavBytes.Num())
    {
        const char* ChunkId = reinterpret_cast<const char*>(D + Offset);
        const int32 ChunkSz = *reinterpret_cast<const int32*>(D + Offset + 4);

        if (FMemory::Memcmp(ChunkId, "fmt ", 4) == 0 && ChunkSz >= 16)
        {
            Out.NumChannels = *reinterpret_cast<const int16*>(D + Offset + 10);
            Out.SampleRate = *reinterpret_cast<const int32*>(D + Offset + 12);
            Out.BitsPerSample = *reinterpret_cast<const int16*>(D + Offset + 22);
            bFoundFmt = true;
        }
        else if (FMemory::Memcmp(ChunkId, "data", 4) == 0)
        {
            if (!bFoundFmt)
                return false;
            Out.DataOffset = Offset + 8;
            Out.DataSize = FMath::Min(ChunkSz, WavBytes.Num() - Out.DataOffset);
            return Out.DataSize > 0;
        }

        Offset += 8 + ChunkSz;
        if (ChunkSz & 1) ++Offset;
    }
    return false;
}
