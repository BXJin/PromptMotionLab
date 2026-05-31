#include "PromptMotionRuntimeComponent.h"
#include "PromptMotionApiClient.h"
#include "PromptMotionLatencyLogger.h"
#include "PromptMotionRealtimeClient.h"
#include "FacePresetResolver.h"
#include "FaceLipSyncLayer.h"
#include "PromptMotionFaceConfig.h"
#include "PromptMotionLog.h"
#include "Components/SkeletalMeshComponent.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "TimerManager.h"

#if PLATFORM_ANDROID
#include "AndroidPermissionCallbackProxy.h"
#include "AndroidPermissionFunctionLibrary.h"
#endif

DEFINE_LOG_CATEGORY(LogPromptMotion);

namespace
{
double ComputeElapsedMs(double StartSeconds, double EndSeconds)
{
    return StartSeconds > 0.0 && EndSeconds > 0.0
        ? (EndSeconds - StartSeconds) * 1000.0
        : -1.0;
}

FString CharacterIdForConversationMode(EPromptMotionConversationMode Mode)
{
    switch (Mode)
    {
    case EPromptMotionConversationMode::EnglishTutor:
        return TEXT("airi_english_tutor");
    case EPromptMotionConversationMode::Guide:
        return TEXT("airi_guide");
    case EPromptMotionConversationMode::Casual:
    default:
        return TEXT("airi");
    }
}
}

UPromptMotionRuntimeComponent::UPromptMotionRuntimeComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = false;

    CharacterPresets = {
        TEXT("airi"),
        TEXT("airi_bright"), TEXT("airi_cheerful"),
        TEXT("airi_idea"), TEXT("airi_direct"),
        TEXT("airi_soft"), TEXT("airi_calm"),
        TEXT("airi_reflective"), TEXT("airi_practical"),
    };
}

void UPromptMotionRuntimeComponent::BeginPlay()
{
    Super::BeginPlay();
    ApplyEndpointConfig();
    LipSyncLayer.LoadMappingsForCharacter(FaceConfigId);
    FFacePresetResolver::LoadCsvForCharacter(FaceConfigId);
    EnsureApiClient();
    ConfigureVoiceInputController();
    ConfigureSpeechPlaybackController();
    RequestMicrophonePermission();
    if (bUseRealtimeWebSocket)
        EnsureRealtimeClient();
    if (bEnableIdleBlink)
        SetComponentTickEnabled(true);
}

void UPromptMotionRuntimeComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    if (VoiceInputController.IsValid())
        VoiceInputController->Shutdown();
    CancelActiveTts();
    IdleFaceLayer.Reset(ResolveTargetMesh());
    SpeechMicroLayer.Reset();
    RealtimeClient.Reset();
    VoiceInputController.Reset();
    SpeechPlaybackController.Reset();
    DebugSttClient.Reset();
    ApiClient.Reset();
    Super::EndPlay(EndPlayReason);
}

void UPromptMotionRuntimeComponent::SendRuntimeMessage(const FString& Message)
{
    SendRuntimeMessageWithContext(Message, FPromptMotionSceneContext{});
}

void UPromptMotionRuntimeComponent::SendRuntimeMessageWithContext(
    const FString& Message,
    const FPromptMotionSceneContext& SceneContext)
{
    const int32 ThisRequestId = RequestIdCounter.Increment();
    if (bUseRealtimeWebSocket)
    {
        SendRuntimeMessageWithWebSocket(Message, SceneContext, ThisRequestId);
        return;
    }

    if (bUseAsyncTurnHttp)
    {
        SendRuntimeMessageWithTurnAsync(Message, SceneContext, ThisRequestId);
        return;
    }

    SendRuntimeMessageWithHttp(Message, SceneContext, ThisRequestId);
}

void UPromptMotionRuntimeComponent::SetCharacterId(const FString& NewCharacterId)
{
    if (CharacterId == NewCharacterId)
        return;

    CharacterId = NewCharacterId;

    // Ï∫êÎ¶≠???ÑÌôò ?????∏ÏÖò ?úÏûë ???¥Ï†Ñ ?Ä???àÏä§?†Î¶¨ ?ûÏûÑ Î∞©Ï?
    SessionId = FString::Printf(TEXT("%s_%lld"), *NewCharacterId, FDateTime::UtcNow().ToUnixTimestamp());

    LipSyncLayer.LoadMappingsForCharacter(FaceConfigId);
    FFacePresetResolver::LoadCsvForCharacter(FaceConfigId);

    UE_LOG(LogPromptMotion, Log, TEXT("[RuntimeComponent] CharacterId=%s FaceConfigId=%s SessionId=%s"),
        *CharacterId, *FaceConfigId, *SessionId);
}

void UPromptMotionRuntimeComponent::SetConversationMode(EPromptMotionConversationMode NewMode)
{
    ConversationMode = NewMode;
    CharacterId = CharacterIdForConversationMode(NewMode);
    LipSyncLayer.LoadMappingsForCharacter(FaceConfigId);
    FFacePresetResolver::LoadCsvForCharacter(FaceConfigId);
}

bool UPromptMotionRuntimeComponent::StartPushToTalk()
{
    if (IsVoiceSubmissionBlocked())
    {
        UE_LOG(LogPromptMotion, Log, TEXT("[STT] PTT ignored while voice pipeline is busy: status=%d"),
            static_cast<int32>(VoiceStatus));
        return false;
    }

    if (bUseDebugSttWavForPushToTalk)
    {
        SetVoiceStatus(EPromptMotionVoiceStatus::UserSpeaking);
        SetComponentTickEnabled(true);
        return true;
    }

    if (!RequestMicrophonePermission())
    {
        SetVoiceStatus(EPromptMotionVoiceStatus::Error);
        return false;
    }

    ConfigureVoiceInputController();
    const double Now = FPlatformTime::Seconds();
    if (!VoiceInputController.IsValid() || !VoiceInputController->StartPushToTalk(Now))
        return false;

    SetVoiceStatus(EPromptMotionVoiceStatus::UserSpeaking);
    SetComponentTickEnabled(true);
    return true;
}

bool UPromptMotionRuntimeComponent::StopPushToTalkAndSend()
{
    if (bUseDebugSttWavForPushToTalk)
        return SubmitDebugSttWav(FPlatformTime::Seconds());

    ConfigureVoiceInputController();
    const double Now = FPlatformTime::Seconds();
    if (!VoiceInputController.IsValid() || !VoiceInputController->StopPushToTalkAndSend(Now))
        return false;
    UE_LOG(LogPromptMotion, Log, TEXT("[VoiceLatency] mic_released world=%.3f"), Now);
    return true;
}

void UPromptMotionRuntimeComponent::SetVoiceVadEnabled(bool bEnabled)
{
    if (bEnabled && !RequestMicrophonePermission())
    {
        SetVoiceStatus(EPromptMotionVoiceStatus::Error);
        return;
    }

    ConfigureVoiceInputController();
    const double Now = FPlatformTime::Seconds();
    if (VoiceInputController.IsValid())
        VoiceInputController->SetVadEnabled(bEnabled, Now);

    if (bEnabled)
    {
        SetVoiceStatus(EPromptMotionVoiceStatus::Listening);
        SetComponentTickEnabled(true);
    }
    else
    {
        SetVoiceStatus(EPromptMotionVoiceStatus::Idle);
    }
}

void UPromptMotionRuntimeComponent::SendRuntimeMessageWithHttp(
    const FString& Message,
    const FPromptMotionSceneContext& SceneContext,
    int32 ThisRequestId)
{
    EnsureApiClient();

    const double LocalReactionStartTime = FPlatformTime::Seconds();
    ApplyFacePreset(TEXT("thinking"), 0.45f);
    const double FirstVisibleReactionMs = (FPlatformTime::Seconds() - LocalReactionStartTime) * 1000.0;



    const double RequestStartTime = FPlatformTime::Seconds();
    AttachVoiceTraceToRequest(ThisRequestId, RequestStartTime);

    UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] Request #%d ??%s | \"%s\""),
        ThisRequestId, *ServerUrl, *Message);

    TWeakObjectPtr<UPromptMotionRuntimeComponent> WeakThis(this);

    ApiClient->SendRuntimeRequest(
        SessionId, CharacterId, Message, SceneContext,
        [WeakThis, ThisRequestId, RequestStartTime, FirstVisibleReactionMs, Message](const FPromptMotionRuntimeResponse& Response)
        {
            UPromptMotionRuntimeComponent* Self = WeakThis.Get();
            if (!Self)
                return;

            // [B] Round-trip latency Êø°Ïíì??
            const double ResponseReceivedTime = FPlatformTime::Seconds();
            const double ElapsedMs = (ResponseReceivedTime - RequestStartTime) * 1000.0;

            // [C] Stale ?Î¨êÎñü ?æÎåÅ????????àÏ§à???Î∂øÍªå????Ä? Ë´õÏíñ???ÂØÉÏéå??
            const int32 CurrentId = Self->RequestIdCounter.GetValue();
            if (ThisRequestId != CurrentId)
            {
                UE_LOG(LogPromptMotion, Log,
                    TEXT("[PromptMotion] Request #%d stale (current=#%d), %.0fms ??discarded"),
                    ThisRequestId, CurrentId, ElapsedMs);
                return;
            }

            if (Response.bSuccess)
            {
                Self->SetVoiceStatus(EPromptMotionVoiceStatus::Thinking);
                Self->LastReply    = Response.Reply;
                Self->LastBehavior = Response.Behavior;

                UE_LOG(LogPromptMotion, Log,
                    TEXT("[PromptMotion] Request #%d OK | %.0fms\n")
                    TEXT("  reply      : %s\n")
                    TEXT("  emotion    : %s (intensity=%.2f)\n")
                    TEXT("  intent     : %s (confidence=%.2f)\n")
                    TEXT("  gestureKey : %s | headMotion : %s | ttsStyle : %s\n")
                    TEXT("  provider   : %s / %s | fallback=%s | server=%dms llm=%dms"),
                    ThisRequestId, ElapsedMs,
                    *Response.Reply,
                    *Response.Behavior.Emotion,   Response.Behavior.Intensity,
                    *Response.Behavior.Intent,    Response.Behavior.Confidence,
                    *Response.Behavior.GestureKey,
                    *Response.Behavior.HeadMotion,
                    *Response.Behavior.TtsStyle,
                    *Response.Metadata.Provider,
                    *Response.Metadata.Model,
                    Response.Metadata.bFallbackUsed ? TEXT("true") : TEXT("false"),
                    Response.Metadata.TotalServerMs,
                    Response.Metadata.ProviderLatencyMs
                );

                // Behavior JSON ??Morph Target ?êÎèô ?ÅÏö©
                Self->ApplyFacePreset(Response.Behavior.Emotion, Response.Behavior.Intensity);
                Self->LastResponseEmotion = Response.Behavior.Emotion;
                Self->LastResponseEmotionAppliedWorldSeconds = Self->GetWorld() ? Self->GetWorld()->GetTimeSeconds() : 0.0;
                Self->StartTtsForResponse(
                    FString::Printf(TEXT("ue_%d"), ThisRequestId),
                    Response.Reply,
                    Response.Behavior.TtsStyle);
            }
            else
            {
                UE_LOG(LogPromptMotion, Warning,
                    TEXT("[PromptMotion] Request #%d FAILED | %.0fms ??%s"),
                    ThisRequestId, ElapsedMs, *Response.ErrorMessage);

                Self->ApplyFacePreset(TEXT("neutral"), 0.0f);
            }

            Self->AppendLatencyCsv(
                ThisRequestId,
                Message,
                Response,
                RequestStartTime,
                ResponseReceivedTime,
                FirstVisibleReactionMs);
            if (Self->ActiveVoiceTrace.RequestId == ThisRequestId)
            {
                Self->ActiveVoiceTrace.LlmReadyWorldSeconds = ResponseReceivedTime;
                Self->AppendVoiceLatencyCsv(&Response, Response.bSuccess ? TEXT("llm_ready") : TEXT("llm_failed"));
            }

            Self->OnRuntimeResponseReceived.Broadcast(Response);
        }
    );
}

void UPromptMotionRuntimeComponent::SendRuntimeMessageWithTurnAsync(
    const FString& Message,
    const FPromptMotionSceneContext& SceneContext,
    int32 ThisRequestId)
{
    EnsureApiClient();

    const double LocalReactionStartTime = FPlatformTime::Seconds();
    ApplyFacePreset(TEXT("thinking"), 0.45f);
    const double FirstVisibleReactionMs = (FPlatformTime::Seconds() - LocalReactionStartTime) * 1000.0;

    const double RequestStartTime = FPlatformTime::Seconds();
    AttachVoiceTraceToRequest(ThisRequestId, RequestStartTime);

    UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] TurnAsync request #%d -> %s | \"%s\""),
        ThisRequestId, *ServerUrl, *Message);

    TWeakObjectPtr<UPromptMotionRuntimeComponent> WeakThis(this);
    ApiClient->SubmitTurnAsyncRequest(
        SessionId, CharacterId, Message, SceneContext,
        [WeakThis, ThisRequestId, RequestStartTime, FirstVisibleReactionMs, Message](const FPromptMotionTurnAsyncAccepted& Accepted)
        {
            UPromptMotionRuntimeComponent* Self = WeakThis.Get();
            if (!Self)
                return;

            const int32 CurrentId = Self->RequestIdCounter.GetValue();
            if (ThisRequestId != CurrentId)
            {
                UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] TurnAsync request #%d stale before submit completion"), ThisRequestId);
                return;
            }

            if (!Accepted.bSuccess)
            {
                const double ResponseReceivedTime = FPlatformTime::Seconds();
                FPromptMotionRuntimeResponse Failed;
                Failed.ErrorMessage = Accepted.ErrorMessage;
                UE_LOG(LogPromptMotion, Warning, TEXT("[PromptMotion] TurnAsync request #%d submit failed: %s"),
                    ThisRequestId, *Accepted.ErrorMessage);
                Self->ApplyFacePreset(TEXT("neutral"), 0.0f);
                Self->AppendLatencyCsv(ThisRequestId, Message, Failed, RequestStartTime, ResponseReceivedTime, FirstVisibleReactionMs);
                Self->OnRuntimeResponseReceived.Broadcast(Failed);
                return;
            }

            Self->TurnJobRequestIds.Add(Accepted.TurnJobId, ThisRequestId);
            Self->TurnJobRequestStartTimes.Add(Accepted.TurnJobId, RequestStartTime);
            Self->TurnJobFirstVisibleMs.Add(Accepted.TurnJobId, FirstVisibleReactionMs);
            Self->TurnJobMessages.Add(Accepted.TurnJobId, Message);

            Self->ApplyFacePreset(Accepted.Reaction.Emotion, Accepted.Reaction.Intensity);
            UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] TurnAsync accepted #%d job=%s status=%s reaction=%s"),
                ThisRequestId, *Accepted.TurnJobId, *Accepted.Status, *Accepted.Reaction.Emotion);
            Self->PollTurnAsyncJob(Accepted.TurnJobId);
        });
}

void UPromptMotionRuntimeComponent::PollTurnAsyncJob(const FString& TurnJobId)
{
    EnsureApiClient();

    TWeakObjectPtr<UPromptMotionRuntimeComponent> WeakThis(this);
    ApiClient->PollTurnAsyncJob(
        TurnJobId,
        [WeakThis, TurnJobId](const FPromptMotionTurnAsyncJob& Job)
        {
            UPromptMotionRuntimeComponent* Self = WeakThis.Get();
            if (!Self)
                return;

            const int32* RequestIdPtr = Self->TurnJobRequestIds.Find(TurnJobId);
            if (!RequestIdPtr)
                return;

            const int32 ThisRequestId = *RequestIdPtr;
            const int32 CurrentId = Self->RequestIdCounter.GetValue();
            if (ThisRequestId != CurrentId)
            {
                UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] TurnAsync job %s stale (request #%d current #%d)"),
                    *TurnJobId, ThisRequestId, CurrentId);
                Self->CleanupTurnAsyncJob(TurnJobId);
                return;
            }

            if (!Job.bSuccess)
            {
                UE_LOG(LogPromptMotion, Warning, TEXT("[PromptMotion] TurnAsync job %s poll failed: %s"),
                    *TurnJobId, *Job.ErrorMessage);
                Self->CleanupTurnAsyncJob(TurnJobId);
                return;
            }

            const bool bAlreadyAppliedResponse = Self->TurnJobResponseApplied.Contains(TurnJobId);
            if (Job.bResponseReady && Job.Response.bSuccess && !bAlreadyAppliedResponse)
            {
                const double ResponseReceivedTime = FPlatformTime::Seconds();
                const double RequestStartTime = Self->TurnJobRequestStartTimes.FindRef(TurnJobId);
                const double FirstVisibleMs = Self->TurnJobFirstVisibleMs.FindRef(TurnJobId);
                const FString Message = Self->TurnJobMessages.FindRef(TurnJobId);
                const double ElapsedMs = RequestStartTime > 0.0
                    ? (ResponseReceivedTime - RequestStartTime) * 1000.0
                    : -1.0;

                Self->SetVoiceStatus(EPromptMotionVoiceStatus::Thinking);
                Self->LastReply = Job.Response.Reply;
                Self->LastBehavior = Job.Response.Behavior;
                Self->ApplyFacePreset(Job.Response.Behavior.Emotion, Job.Response.Behavior.Intensity);
                Self->LastResponseEmotion = Job.Response.Behavior.Emotion;
                Self->LastResponseEmotionAppliedWorldSeconds = Self->GetWorld() ? Self->GetWorld()->GetTimeSeconds() : 0.0;
                Self->TurnJobResponseApplied.Add(TurnJobId);

                UE_LOG(LogPromptMotion, Log,
                    TEXT("[PromptMotion] TurnAsync response #%d OK | %.0fms job=%s\n")
                    TEXT("  reply      : %s\n")
                    TEXT("  emotion    : %s (intensity=%.2f)\n")
                    TEXT("  provider   : %s / %s | fallback=%s | server=%dms llm=%dms"),
                    ThisRequestId, ElapsedMs, *TurnJobId,
                    *Job.Response.Reply,
                    *Job.Response.Behavior.Emotion, Job.Response.Behavior.Intensity,
                    *Job.Response.Metadata.Provider,
                    *Job.Response.Metadata.Model,
                    Job.Response.Metadata.bFallbackUsed ? TEXT("true") : TEXT("false"),
                    Job.Response.Metadata.TotalServerMs,
                    Job.Response.Metadata.ProviderLatencyMs);

                Self->AppendLatencyCsv(
                    ThisRequestId,
                    Message,
                    Job.Response,
                    RequestStartTime,
                    ResponseReceivedTime,
                    FirstVisibleMs);

                if (Self->ActiveVoiceTrace.RequestId == ThisRequestId)
                {
                    Self->ActiveVoiceTrace.LlmReadyWorldSeconds = ResponseReceivedTime;
                    UE_LOG(LogPromptMotion, Log,
                        TEXT("[VoiceLatency] llm_ready request=%d speechEndToLlmMs=%.0f sttFinalToLlmMs=%.0f llmRequestToReadyMs=%.0f"),
                        ThisRequestId,
                        ComputeElapsedMs(Self->ActiveVoiceTrace.SpeechEndWorldSeconds, Self->ActiveVoiceTrace.LlmReadyWorldSeconds),
                        ComputeElapsedMs(Self->ActiveVoiceTrace.SttReadyWorldSeconds, Self->ActiveVoiceTrace.LlmReadyWorldSeconds),
                        ComputeElapsedMs(Self->ActiveVoiceTrace.LlmRequestSentWorldSeconds, Self->ActiveVoiceTrace.LlmReadyWorldSeconds));
                    Self->AppendVoiceLatencyCsv(&Job.Response, TEXT("llm_ready"));
                }

                Self->OnRuntimeResponseReceived.Broadcast(Job.Response);
            }

            if (Job.bTtsReady && !Job.SpeechTimeline.UtteranceId.IsEmpty())
            {
                if (!Self->TurnJobTtsStarted.Contains(TurnJobId))
                {
                    Self->TurnJobTtsStarted.Add(TurnJobId);
                    UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] TurnAsync first TTS segment ready job=%s segments=%d"),
                        *TurnJobId, Job.SpeechTimeline.Segments.Num());
                }
                Self->StartTtsTimelineForResponse(FString::Printf(TEXT("ue_%d"), ThisRequestId), Job.SpeechTimeline);
            }

            const bool bFinished = Job.Status.Equals(TEXT("succeeded"), ESearchCase::IgnoreCase)
                || Job.Status.Equals(TEXT("failed"), ESearchCase::IgnoreCase);
            if (bFinished)
            {
                if (Job.Status.Equals(TEXT("failed"), ESearchCase::IgnoreCase))
                {
                    UE_LOG(LogPromptMotion, Warning, TEXT("[PromptMotion] TurnAsync job %s failed: %s"),
                        *TurnJobId, *Job.ErrorMessage);
                    if (Self->TurnJobResponseApplied.Contains(TurnJobId))
                    {
                        Self->LastTtsStopWorldSeconds = Self->GetWorld() ? Self->GetWorld()->GetTimeSeconds() : 0.0;
                        Self->SetVoiceStatus(EPromptMotionVoiceStatus::Cooldown);
                        if (Self->ActiveVoiceTrace.RequestId == ThisRequestId)
                            Self->AppendVoiceLatencyCsv(&Job.Response, TEXT("tts_failed_after_response"));
                    }
                    else
                    {
                        FPromptMotionRuntimeResponse Failed;
                        Failed.ErrorMessage = Job.ErrorMessage;
                        Self->SetVoiceStatus(EPromptMotionVoiceStatus::Error);
                        Self->OnRuntimeResponseReceived.Broadcast(Failed);
                    }
                }

                Self->CleanupTurnAsyncJob(TurnJobId);
                return;
            }

            UWorld* World = Self->GetWorld();
            if (!World)
                return;

            FTimerHandle PollHandle;
            World->GetTimerManager().SetTimer(
                PollHandle,
                FTimerDelegate::CreateWeakLambda(Self, [WeakThis, TurnJobId]()
                {
                    if (UPromptMotionRuntimeComponent* Runtime = WeakThis.Get())
                        Runtime->PollTurnAsyncJob(TurnJobId);
                }),
                FMath::Max(0.05f, Self->AsyncTurnPollIntervalSeconds),
                false);
        });
}

void UPromptMotionRuntimeComponent::CleanupTurnAsyncJob(const FString& TurnJobId)
{
    TurnJobRequestIds.Remove(TurnJobId);
    TurnJobRequestStartTimes.Remove(TurnJobId);
    TurnJobFirstVisibleMs.Remove(TurnJobId);
    TurnJobMessages.Remove(TurnJobId);
    TurnJobResponseApplied.Remove(TurnJobId);
    TurnJobTtsStarted.Remove(TurnJobId);
}

void UPromptMotionRuntimeComponent::SendRuntimeMessageWithWebSocket(
    const FString& Message,
    const FPromptMotionSceneContext& SceneContext,
    int32 ThisRequestId)
{
    EnsureRealtimeClient();

    if (!RealtimeClient.IsValid() || !RealtimeClient->IsConnected())
    {
        const FString RequestIdText = FString::Printf(TEXT("ue_%d"), ThisRequestId);
        ActiveRealtimeRequestId = RequestIdText;
        RealtimeRequestStartTimes.Add(RequestIdText, FPlatformTime::Seconds());
        AttachVoiceTraceToRequest(ThisRequestId, RealtimeRequestStartTimes.FindRef(RequestIdText));
        RealtimeMessages.Add(RequestIdText, Message);

        const double LocalReactionStartTime = FPlatformTime::Seconds();
        ApplyFacePreset(TEXT("thinking"), 0.45f);
        const double FirstVisibleReactionMs = (FPlatformTime::Seconds() - LocalReactionStartTime) * 1000.0;
        RealtimeFirstVisibleMs.Add(RequestIdText, FirstVisibleReactionMs);

        PendingRealtimeRequests.Add(FPendingRealtimeRequest{ThisRequestId, Message, SceneContext});
        UE_LOG(LogPromptMotion, Warning,
            TEXT("[PromptMotion] WebSocket not connected; queued request #%d until connection opens"),
            ThisRequestId);
        return;
    }

    const FString RequestIdText = FString::Printf(TEXT("ue_%d"), ThisRequestId);
    ActiveRealtimeRequestId = RequestIdText;
    if (!RealtimeRequestStartTimes.Contains(RequestIdText))
    {
        RealtimeRequestStartTimes.Add(RequestIdText, FPlatformTime::Seconds());
    }
    AttachVoiceTraceToRequest(ThisRequestId, RealtimeRequestStartTimes.FindRef(RequestIdText));
    if (!RealtimeFirstVisibleMs.Contains(RequestIdText))
    {
        RealtimeFirstVisibleMs.Add(RequestIdText, -1.0);
    }
    RealtimeMessages.FindOrAdd(RequestIdText) = Message;

    UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] WS Request #%d -> %s | \"%s\""),
        ThisRequestId, *WebSocketUrl, *Message);

    RealtimeClient->SendRuntimeRequest(
        RequestIdText,
        SessionId,
        CharacterId,
        Message,
        SceneContext);
}

void UPromptMotionRuntimeComponent::ApplyFacePreset(const FString& Emotion, float Intensity)
{
    if (!ResolveTargetMesh())
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[PromptMotion] ApplyFacePreset: TargetMesh not found on '%s'"),
            GetOwner() ? *GetOwner()->GetName() : TEXT("null"));
        return;
    }

    const float RuntimeIntensity = RemapExpressionIntensity(Intensity);
    TargetFaceSettings = FFacePresetResolver::ResolveSettings(Emotion, RuntimeIntensity, FaceConfigId);
    TargetWeights.Reset();
    for (const auto& Pair : TargetFaceSettings)
        TargetWeights.FindOrAdd(Pair.Key) = Pair.Value.Weight;

    // CurrentWeights????øÎíó morph??0?Î®?Ωå ??ñÏòâ (Ôß??âÎ∂æ????Î®?íó ??morph)
    for (const auto& Pair : TargetWeights)
    {
        CurrentWeights.FindOrAdd(Pair.Key, 0.0f);
    }

    const float RequestedBlendDuration = NextBlendDurationOverride >= 0.0f ? NextBlendDurationOverride : BlendDuration;
    NextBlendDurationOverride = -1.0f;

    if (RequestedBlendDuration > SMALL_NUMBER)
    {
        // ?âÎ∂æ?????ñÏòâ ??ñÏ†è??weight ??ªÍπÑ????Tick?Î®?Ωå ?Ï¢èÏÇé ËπÇÎãøÏª??AÂ™õÎ??ùÊø°?????
        InitialWeights = CurrentWeights;
        // InitialWeights????øÎíó ?Ï¢âÌáã morph??0?Î®?Ωå ??ñÏòâ
        for (const auto& Pair : TargetWeights)
            InitialWeights.FindOrAdd(Pair.Key, 0.0f);

        BlendElapsed = 0.0f;
        ActiveBlendDuration = RequestedBlendDuration;
        bFaceBlendActive = true;
        SetComponentTickEnabled(true);

        UE_LOG(LogPromptMotion, Log,
            TEXT("[PromptMotion] FacePreset blend started ??emotion=%s intensity=%.2f runtimeIntensity=%.2f duration=%.2fs morphs=%d"),
            *Emotion, Intensity, RuntimeIntensity, ActiveBlendDuration, TargetWeights.Num());
    }
    else
    {
        // BlendDuration = 0??Ä??ÔßùÎê±???Í≥∏Ïäú
        USkeletalMeshComponent* Mesh = ResolveTargetMesh();
        CurrentWeights.Reset();
        ActiveBlendDuration = 0.0f;
        bFaceBlendActive = false;
        for (const auto& Pair : TargetFaceSettings)
        {
            const float Effective = GetEffectiveFaceWeight(Pair.Key, Pair.Value);
            CurrentWeights.FindOrAdd(Pair.Key) = Effective;
            Mesh->SetMorphTarget(Pair.Key, Effective);
        }

        UE_LOG(LogPromptMotion, Log,
            TEXT("[PromptMotion] FacePreset applied (instant) ??emotion=%s intensity=%.2f runtimeIntensity=%.2f morphs=%d"),
            *Emotion, Intensity, RuntimeIntensity, CurrentWeights.Num());
    }
}

void UPromptMotionRuntimeComponent::ReloadFaceConfig()
{
    LipSyncLayer.LoadMappingsForCharacter(FaceConfigId);
    FFacePresetResolver::LoadCsvForCharacter(FaceConfigId);
    UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] Face config reloaded: faceConfig=%s character=%s"),
        *FaceConfigId, *CharacterId);
}

float UPromptMotionRuntimeComponent::RemapExpressionIntensity(float Intensity) const
{
    const float ClampedInput = FMath::Clamp(Intensity, 0.0f, 1.0f);
    if (ClampedInput <= SMALL_NUMBER)
        return 0.0f;

    const float MinValue = FMath::Clamp(ExpressionIntensityMin, 0.0f, 2.0f);
    const float MaxValue = FMath::Clamp(ExpressionIntensityMax, 0.0f, 2.0f);
    const float Lower = FMath::Min(MinValue, MaxValue);
    const float Upper = FMath::Max(MinValue, MaxValue);
    const float Remapped = FMath::Lerp(Lower, Upper, ClampedInput);
    return FMath::Clamp(Remapped * ExpressionIntensityMultiplier, 0.0f, 2.0f);
}

float UPromptMotionRuntimeComponent::GetEffectiveFaceWeight(FName MorphName, const FPromptMotionFaceMorphSetting& Setting) const
{
    float Weight = Setting.Weight;
    if (bLipSyncActive && Setting.LipSyncMask > 0.0f)
        Weight *= FMath::Clamp(Setting.LipSyncMask, 0.0f, 1.0f);
    return FMath::Clamp(Weight, -1.0f, 1.0f);
}

float UPromptMotionRuntimeComponent::GetFaceInterpSpeed(FName MorphName, float Current, float Target) const
{
    const FPromptMotionFaceMorphSetting* Setting = TargetFaceSettings.Find(MorphName);
    const float FadeSec = Setting
        ? (Target >= Current ? Setting->FadeInSec : Setting->FadeOutSec)
        : BlendDuration;
    return FadeSec <= SMALL_NUMBER ? 1000.0f : 4.0f / FadeSec;
}

void UPromptMotionRuntimeComponent::ApplySpeechMicroOffsets(USkeletalMeshComponent* Mesh)
{
    if (!Mesh || !bEnableSpeechMicroExpression)
        return;

    for (const auto& Pair : SpeechMicroLayer.GetOffsets())
    {
        const float Base = CurrentWeights.FindRef(Pair.Key);
        Mesh->SetMorphTarget(Pair.Key, FMath::Clamp(Base + Pair.Value, 0.0f, 1.0f));
    }
}

void UPromptMotionRuntimeComponent::ApplyIdleExpressionIfNeeded(float)
{
    const bool bVoiceBusy = VoiceInputController.IsValid()
        && (VoiceInputController->IsPushToTalkActive() || VoiceInputController->IsVadSpeechActive());
    if (!bEnableIdleExpression || bLipSyncActive || bFaceBlendActive || bVoiceBusy)
        return;

    UWorld* World = GetWorld();
    if (!World)
        return;

    const double Now = World->GetTimeSeconds();
    if (Now - LastResponseEmotionAppliedWorldSeconds < ResponseEmotionHoldSeconds)
        return;

    const FString IdleEmotion = ResolveIdleEmotion();
    const float IdleIntensity = ResolveIdleIntensity();
    if (LastResponseEmotion.Equals(IdleEmotion, ESearchCase::IgnoreCase) && !TargetFaceSettings.IsEmpty())
        return;

    NextBlendDurationOverride = FMath::Max(0.1f, ResponseEmotionDecaySeconds);
    ApplyFacePreset(IdleEmotion, IdleIntensity);
    LastResponseEmotion = IdleEmotion;
    LastResponseEmotionAppliedWorldSeconds = Now + FMath::Max(0.0f, ResponseEmotionDecaySeconds);
}

FString UPromptMotionRuntimeComponent::ResolveIdleEmotion() const
{
    const FString Key = CharacterId.ToLower();
    if (Key.StartsWith(TEXT("e_f")))
        return FMath::FRand() < 0.65f ? TEXT("friendly") : TEXT("curious");
    if (Key.StartsWith(TEXT("e_t")))
        return FMath::FRand() < 0.70f ? TEXT("friendly") : TEXT("thinking");
    if (Key.StartsWith(TEXT("i_t")))
        return TEXT("thinking");
    if (Key.StartsWith(TEXT("i_f")))
        return FMath::FRand() < 0.75f ? TEXT("listening") : TEXT("friendly");
    return TEXT("listening");
}

float UPromptMotionRuntimeComponent::ResolveIdleIntensity() const
{
    const FString Key = CharacterId.ToLower();
    float Scale = 1.0f;
    if (Key.StartsWith(TEXT("e_")))
        Scale = 1.15f;
    else if (Key.StartsWith(TEXT("i_")))
        Scale = 0.80f;
    return FMath::Clamp(IdleExpressionIntensity * Scale, 0.0f, 0.5f);
}

void UPromptMotionRuntimeComponent::ApplyDebugMorph(FName MorphName, float Weight)
{
    if (!bAllowDebugMorphControl || MorphName.IsNone())
        return;

    USkeletalMeshComponent* Mesh = ResolveTargetMesh();
    if (!Mesh)
        return;

    Mesh->SetMorphTarget(MorphName, FMath::Clamp(Weight, -1.0f, 1.0f));
}

void UPromptMotionRuntimeComponent::ApplyDebugViseme(int32 VisemeId, float Weight)
{
    if (!bAllowDebugMorphControl)
        return;

    USkeletalMeshComponent* Mesh = ResolveTargetMesh();
    if (!Mesh)
        return;

    LipSyncLayer.ApplyViseme(VisemeId, FMath::Clamp(Weight, 0.0f, 1.0f), Mesh);
    LipSyncLayer.Update(1.0f, Mesh); // debug: DeltaTime ?¨Í≤å Ï§òÏÑú Ï¶âÏãú ?òÎ†¥
}

bool UPromptMotionRuntimeComponent::SaveDebugLipSyncVisemeWeight(int32 VisemeId, FName MorphName, float Weight)
{
    if (!bAllowDebugMorphControl || VisemeId < 0 || VisemeId > 21 || MorphName.IsNone())
        return false;

    const FString CsvPath = FPromptMotionFaceConfig::GetLipSyncVisemeCsvPath(FaceConfigId);
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(CsvPath), true);

    TArray<FString> Lines;
    FFileHelper::LoadFileToStringArray(Lines, *CsvPath);
    if (Lines.IsEmpty())
        Lines.Add(TEXT("viseme_id,morph_name,weight,fade_in_sec,fade_out_sec"));
    else if (Lines[0].TrimStartAndEnd().Equals(TEXT("viseme_id,morph_name,weight"), ESearchCase::IgnoreCase))
        Lines[0] = TEXT("viseme_id,morph_name,weight,fade_in_sec,fade_out_sec");

    const FString VisemeText = FString::FromInt(VisemeId);
    const FString MorphText = MorphName.ToString();
    const float ClampedWeight = FMath::Clamp(Weight, -1.0f, 1.0f);
    const FString NewLine = FString::Printf(TEXT("%d,%s,%.3f,0.050,0.080"), VisemeId, *MorphText, ClampedWeight);
    bool bReplaced = false;

    for (int32 Index = 1; Index < Lines.Num(); ++Index)
    {
        TArray<FString> Cells;
        Lines[Index].ParseIntoArray(Cells, TEXT(","), false);
        if (Cells.Num() < 2)
            continue;

        if (Cells[0].TrimStartAndEnd() == VisemeText &&
            Cells[1].TrimStartAndEnd().Equals(MorphText, ESearchCase::IgnoreCase))
        {
            while (Cells.Num() < 5)
                Cells.Add(Cells.Num() == 3 ? TEXT("0.050") : TEXT("0.080"));
            Cells[2] = FString::Printf(TEXT("%.3f"), ClampedWeight);
            Lines[Index] = FString::Join(Cells, TEXT(","));
            bReplaced = true;
            break;
        }
    }

    if (!bReplaced)
        Lines.Add(NewLine);

    const bool bSaved = FFileHelper::SaveStringArrayToFile(Lines, *CsvPath);
    if (bSaved)
        ReloadFaceConfig();

    UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] LipSync CSV save %s: %s"),
        bSaved ? TEXT("OK") : TEXT("FAILED"), *CsvPath);
    return bSaved;
}

bool UPromptMotionRuntimeComponent::SaveDebugFacePresetWeight(const FString& Preset, FName MorphName, float Weight)
{
    const FString CleanPreset = Preset.TrimStartAndEnd();
    if (!bAllowDebugMorphControl || CleanPreset.IsEmpty() || MorphName.IsNone())
        return false;

    const FString CsvPath = FPromptMotionFaceConfig::GetFacePresetCsvPath(FaceConfigId);
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(CsvPath), true);

    TArray<FString> Lines;
    FFileHelper::LoadFileToStringArray(Lines, *CsvPath);
    if (Lines.IsEmpty())
        Lines.Add(TEXT("preset,morph_name,weight,blend_mode,fade_in_sec,fade_out_sec,lip_sync_mask,conflict_group"));
    else if (Lines[0].TrimStartAndEnd().Equals(TEXT("preset,morph_name,weight"), ESearchCase::IgnoreCase))
        Lines[0] = TEXT("preset,morph_name,weight,blend_mode,fade_in_sec,fade_out_sec,lip_sync_mask,conflict_group");

    const FString MorphText = MorphName.ToString();
    const FString NewLine = FString::Printf(TEXT("%s,%s,%.3f,Additive,0.180,0.240,0.000,"), *CleanPreset, *MorphText, FMath::Clamp(Weight, -1.0f, 1.0f));
    bool bReplaced = false;

    for (int32 Index = 1; Index < Lines.Num(); ++Index)
    {
        TArray<FString> Cells;
        Lines[Index].ParseIntoArray(Cells, TEXT(","), false);
        if (Cells.Num() < 2)
            continue;

        if (Cells[0].TrimStartAndEnd().Equals(CleanPreset, ESearchCase::IgnoreCase) &&
            Cells[1].TrimStartAndEnd().Equals(MorphText, ESearchCase::IgnoreCase))
        {
            while (Cells.Num() < 8)
            {
                static const TCHAR* Defaults[] = { TEXT(""), TEXT(""), TEXT("0.000"), TEXT("Additive"), TEXT("0.180"), TEXT("0.240"), TEXT("0.000"), TEXT("") };
                Cells.Add(Defaults[Cells.Num()]);
            }
            Cells[2] = FString::Printf(TEXT("%.3f"), FMath::Clamp(Weight, -1.0f, 1.0f));
            Lines[Index] = FString::Join(Cells, TEXT(","));
            bReplaced = true;
            break;
        }
    }

    if (!bReplaced)
        Lines.Add(NewLine);

    const bool bSaved = FFileHelper::SaveStringArrayToFile(Lines, *CsvPath);
    UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] FacePreset CSV save %s: %s"),
        bSaved ? TEXT("OK") : TEXT("FAILED"), *CsvPath);
    return bSaved;
}

float UPromptMotionRuntimeComponent::QueryDebugFaceWeight(const FString& Preset, FName MorphName) const
{
    return FFacePresetResolver::QueryWeight(Preset, MorphName, FaceConfigId);
}

float UPromptMotionRuntimeComponent::QueryDebugVisemeWeight(int32 VisemeId, FName MorphName) const
{
    return LipSyncLayer.QueryVisemeWeight(VisemeId, MorphName);
}

void UPromptMotionRuntimeComponent::TickComponent(
    float DeltaTime,
    ELevelTick TickType,
    FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

    if (VoiceInputController.IsValid())
        VoiceInputController->Tick(FPlatformTime::Seconds());
    if (VoiceStatus == EPromptMotionVoiceStatus::Cooldown)
    {
        const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
        if (Now - LastTtsStopWorldSeconds >= VoiceTtsCooldownSeconds)
            SetVoiceStatus(VoiceInputController.IsValid() && VoiceInputController->IsVadEnabled()
                ? EPromptMotionVoiceStatus::Listening
                : EPromptMotionVoiceStatus::Idle);
    }
    else if (VoiceStatus == EPromptMotionVoiceStatus::Error && bMicrophonePermissionGranted)
    {
        const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
        if (Now - VoiceErrorStartedWorldSeconds >= VoiceErrorHoldSeconds)
            SetVoiceStatus(VoiceInputController.IsValid() && VoiceInputController->IsVadEnabled()
                ? EPromptMotionVoiceStatus::Listening
                : EPromptMotionVoiceStatus::Idle);
    }

    USkeletalMeshComponent* Mesh = ResolveTargetMesh();
    if (!Mesh)
    {
        StopLipSyncTimeline();
        bFaceBlendActive = false;
        if (!IsVoiceInputActive() && VoiceStatus != EPromptMotionVoiceStatus::Cooldown)
            SetComponentTickEnabled(false);
        return;
    }

    if (bEnableIdleBlink)
        IdleFaceLayer.Update(DeltaTime, Mesh, bLipSyncActive);
    const bool bVoiceBusy = VoiceInputController.IsValid()
        && (VoiceInputController->IsPushToTalkActive() || VoiceInputController->IsVadSpeechActive());
    const bool bIdleFaceActive = bEnableIdleExpression && !bLipSyncActive && !bFaceBlendActive && !bVoiceBusy;
    if (bEnableSpeechMicroExpression)
        SpeechMicroLayer.Update(DeltaTime, bLipSyncActive, bIdleFaceActive, LastBehavior.Emotion);
    ApplyIdleExpressionIfNeeded(DeltaTime);

    if (!bFaceBlendActive || TargetWeights.IsEmpty())
    {
        if (bLipSyncActive)
        {
            const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
            const float AudioSeconds = static_cast<float>(FMath::Max(0.0, Now - LipSyncStartWorldSeconds));
            UpdateLipSyncFromAudioTime(AudioSeconds);
            LipSyncLayer.Update(DeltaTime, Mesh);
        }
        ApplySpeechMicroOffsets(Mesh);
        if (!bLipSyncActive && !bEnableIdleBlink && !SpeechMicroLayer.HasActiveOffsets() && !IsVoiceInputActive() && VoiceStatus != EPromptMotionVoiceStatus::Cooldown)
        {
            SetComponentTickEnabled(false);
        }
        return;
    }

    BlendElapsed += DeltaTime;
    const float BlendTime = ActiveBlendDuration > SMALL_NUMBER ? ActiveBlendDuration : BlendDuration;
    const float Alpha = FMath::Clamp(BlendElapsed / BlendTime, 0.0f, 1.0f);

    for (const auto& Pair : TargetWeights)
    {
        const FPromptMotionFaceMorphSetting* Setting = TargetFaceSettings.Find(Pair.Key);
        const float Target = Setting ? GetEffectiveFaceWeight(Pair.Key, *Setting) : Pair.Value;
        const float Current = CurrentWeights.FindRef(Pair.Key);
        const float Blended = FMath::FInterpTo(Current, Target, DeltaTime, GetFaceInterpSpeed(Pair.Key, Current, Target));
        CurrentWeights.FindOrAdd(Pair.Key) = Blended;
        Mesh->SetMorphTarget(Pair.Key, Blended);
    }
    if (Alpha >= 1.0f)
    {
        // ?âÎ∂æ????Íæ®Ï¶∫ ??Ôßè‚ë∫Î™¥Â™õÎØ™ÏëùÊø??Î∫§Ï†ô??çÌÄ?Tick ??æ™??ÍπäÏÜï
        CurrentWeights.Reset();
        for (const auto& TargetPair : TargetFaceSettings)
            CurrentWeights.FindOrAdd(TargetPair.Key) = GetEffectiveFaceWeight(TargetPair.Key, TargetPair.Value);
        bFaceBlendActive = false;
        ActiveBlendDuration = 0.0f;
        if (!bLipSyncActive && !bEnableIdleBlink && !SpeechMicroLayer.HasActiveOffsets() && !IsVoiceInputActive() && VoiceStatus != EPromptMotionVoiceStatus::Cooldown)
        {
            SetComponentTickEnabled(false);
        }

        UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] FacePreset blend complete ??%.0fms elapsed"),
            BlendElapsed * 1000.0f);
    }

    if (bLipSyncActive)
    {
        const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
        const float AudioSeconds = static_cast<float>(FMath::Max(0.0, Now - LipSyncStartWorldSeconds));
        UpdateLipSyncFromAudioTime(AudioSeconds);
        LipSyncLayer.Update(DeltaTime, Mesh);
    }
    ApplySpeechMicroOffsets(Mesh);

    if (!bFaceBlendActive && !bLipSyncActive && !bEnableIdleBlink && !SpeechMicroLayer.HasActiveOffsets() && !IsVoiceInputActive() && VoiceStatus != EPromptMotionVoiceStatus::Cooldown)
    {
        SetComponentTickEnabled(false);
    }
}

USkeletalMeshComponent* UPromptMotionRuntimeComponent::ResolveTargetMesh() const
{
    if (TargetMesh.Get())
        return TargetMesh.Get();

    AActor* Owner = GetOwner();
    if (!Owner)
        return nullptr;

    return Owner->FindComponentByClass<USkeletalMeshComponent>();
}

void UPromptMotionRuntimeComponent::ApplyEndpointConfig()
{
    if (!bLoadEndpointConfigOnBeginPlay)
        return;

    FPromptMotionRuntimeEndpointConfig Config;
    Config.ServerUrl = ServerUrl;
    Config.RuntimeWebSocketUrl = WebSocketUrl;
    Config.StreamingSttWebSocketUrl = StreamingSttWebSocketUrl;
    Config.bUseRealtimeWebSocket = bUseRealtimeWebSocket;
    Config.bUseAsyncTurnHttp = bUseAsyncTurnHttp;
    Config.bEnableStreamingStt = bEnableStreamingStt;

    if (!Config.LoadFromConfig(EndpointConfigProfileOverride))
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[RuntimeConfig] Endpoint config not found; using component values"));
        return;
    }

    ServerUrl = Config.ServerUrl.TrimEnd();
    WebSocketUrl = Config.RuntimeWebSocketUrl;
    StreamingSttWebSocketUrl = Config.StreamingSttWebSocketUrl;
    bUseRealtimeWebSocket = Config.bUseRealtimeWebSocket;
    bUseAsyncTurnHttp = Config.bUseAsyncTurnHttp;
    bEnableStreamingStt = Config.bEnableStreamingStt;

    UE_LOG(LogPromptMotion, Log, TEXT("[RuntimeConfig] profile=%s server=%s runtimeWs=%s streamingSttWs=%s asyncTurn=%s realtimeWs=%s streamingStt=%s"),
        *Config.ActiveProfile,
        *ServerUrl,
        *WebSocketUrl,
        *StreamingSttWebSocketUrl,
        bUseAsyncTurnHttp ? TEXT("true") : TEXT("false"),
        bUseRealtimeWebSocket ? TEXT("true") : TEXT("false"),
        bEnableStreamingStt ? TEXT("true") : TEXT("false"));
}
void UPromptMotionRuntimeComponent::EnsureApiClient()
{
    if (!ApiClient.IsValid() || CachedBaseUrl != ServerUrl)
    {
        CachedBaseUrl = ServerUrl;
        ApiClient = MakeUnique<FPromptMotionApiClient>(ServerUrl);
    }
}

void UPromptMotionRuntimeComponent::EnsureRealtimeClient()
{
    if (RealtimeClient.IsValid() && CachedWebSocketUrl == WebSocketUrl)
    {
        if (!RealtimeClient->IsConnected())
        {
            RealtimeClient->Connect();
        }
        return;
    }

    CachedWebSocketUrl = WebSocketUrl;
    RealtimeClient = MakeUnique<FPromptMotionRealtimeClient>(WebSocketUrl);

    TWeakObjectPtr<UPromptMotionRuntimeComponent> WeakThis(this);
    RealtimeClient->OnConnected = [WeakThis]()
    {
        UPromptMotionRuntimeComponent* Self = WeakThis.Get();
        if (Self)
        {
            Self->FlushPendingRealtimeRequests();
        }
    };

    RealtimeClient->OnReaction = [WeakThis](const FString& RequestId, const FPromptMotionBehavior& Behavior)
    {
        UPromptMotionRuntimeComponent* Self = WeakThis.Get();
        if (!Self || Self->IsStaleRealtimeRequest(RequestId))
        {
            return;
        }

        const double Started = FPlatformTime::Seconds();
        Self->ApplyFacePreset(Behavior.Emotion, Behavior.Intensity);
        const double FirstVisibleMs = (FPlatformTime::Seconds() - Started) * 1000.0;
        Self->RealtimeFirstVisibleMs.FindOrAdd(RequestId) = FirstVisibleMs;

        UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] WS reaction %s emotion=%s intensity=%.2f"),
            *RequestId, *Behavior.Emotion, Behavior.Intensity);
    };

    RealtimeClient->OnFinal = [WeakThis](const FString& RequestId, const FPromptMotionRuntimeResponse& Response)
    {
        UPromptMotionRuntimeComponent* Self = WeakThis.Get();
        if (!Self || Self->IsStaleRealtimeRequest(RequestId))
        {
            return;
        }

        const double ResponseReceivedTime = FPlatformTime::Seconds();
        const double RequestStartTime = Self->RealtimeRequestStartTimes.FindRef(RequestId);
        const double FirstVisibleMs = Self->RealtimeFirstVisibleMs.FindRef(RequestId);
        const FString Message = Self->RealtimeMessages.FindRef(RequestId);
        const int32 NumericRequestId = Self->ParseUnrealRequestId(RequestId);
        const double ElapsedMs = RequestStartTime > 0.0 ? (ResponseReceivedTime - RequestStartTime) * 1000.0 : -1.0;

        if (Response.bSuccess)
        {
            Self->SetVoiceStatus(EPromptMotionVoiceStatus::Thinking);
            Self->LastReply = Response.Reply;
            Self->LastBehavior = Response.Behavior;
            Self->ApplyFacePreset(Response.Behavior.Emotion, Response.Behavior.Intensity);
            Self->LastResponseEmotion = Response.Behavior.Emotion;
            Self->LastResponseEmotionAppliedWorldSeconds = Self->GetWorld() ? Self->GetWorld()->GetTimeSeconds() : 0.0;
            Self->StartTtsForResponse(RequestId, Response.Reply, Response.Behavior.TtsStyle);

            UE_LOG(LogPromptMotion, Log,
                TEXT("[PromptMotion] WS final %s OK | %.0fms\n")
                TEXT("  reply      : %s\n")
                TEXT("  emotion    : %s (intensity=%.2f)\n")
                TEXT("  provider   : %s / %s | fallback=%s | server=%dms llm=%dms"),
                *RequestId, ElapsedMs,
                *Response.Reply,
                *Response.Behavior.Emotion, Response.Behavior.Intensity,
                *Response.Metadata.Provider,
                *Response.Metadata.Model,
                Response.Metadata.bFallbackUsed ? TEXT("true") : TEXT("false"),
                Response.Metadata.TotalServerMs,
                Response.Metadata.ProviderLatencyMs);
        }
        else
        {
            UE_LOG(LogPromptMotion, Warning, TEXT("[PromptMotion] WS final %s failed: %s"),
                *RequestId, *Response.ErrorMessage);
            Self->ApplyFacePreset(TEXT("neutral"), 0.0f);
        }

        Self->AppendLatencyCsv(
            NumericRequestId,
            Message,
            Response,
            RequestStartTime,
            ResponseReceivedTime,
            FirstVisibleMs);
        if (Self->ActiveVoiceTrace.RequestId == NumericRequestId)
        {
            Self->ActiveVoiceTrace.LlmReadyWorldSeconds = ResponseReceivedTime;
            Self->AppendVoiceLatencyCsv(&Response, Response.bSuccess ? TEXT("llm_ready") : TEXT("llm_failed"));
        }

        Self->OnRuntimeResponseReceived.Broadcast(Response);
        Self->RealtimeRequestStartTimes.Remove(RequestId);
        Self->RealtimeFirstVisibleMs.Remove(RequestId);
        Self->RealtimeMessages.Remove(RequestId);
    };

    RealtimeClient->OnError = [WeakThis](const FString& RequestId, const FString& ErrorMessage)
    {
        UPromptMotionRuntimeComponent* Self = WeakThis.Get();
        if (!Self)
        {
            return;
        }
        UE_LOG(LogPromptMotion, Warning, TEXT("[PromptMotion] WS error request=%s error=%s"),
            *RequestId, *ErrorMessage);
        if (RequestId.IsEmpty())
        {
            Self->FallbackPendingRealtimeRequests(ErrorMessage);
        }
    };

    RealtimeClient->OnClosed = [WeakThis](const FString& Reason)
    {
        UPromptMotionRuntimeComponent* Self = WeakThis.Get();
        if (Self)
        {
            Self->FallbackPendingRealtimeRequests(Reason);
        }
    };

    RealtimeClient->Connect();
}

void UPromptMotionRuntimeComponent::ConfigureVoiceInputController()
{
    if (!VoiceInputController.IsValid())
        VoiceInputController = MakeShared<FPromptMotionVoiceInputController>();

    FPromptMotionVoiceInputSettings Settings;
    Settings.ServerUrl = ServerUrl;
    Settings.StreamingSttWebSocketUrl = StreamingSttWebSocketUrl;
    Settings.Language = SttLanguage;
    Settings.SampleRate = VoiceSampleRate;
    Settings.VadStartRmsThreshold = VadStartRmsThreshold;
    Settings.VadEndRmsThreshold = VadEndRmsThreshold;
    Settings.VadMinSpeechSeconds = VadMinSpeechSeconds;
    Settings.VadEndSilenceSeconds = VadEndSilenceSeconds;
    Settings.PollIntervalSeconds = VoicePollIntervalSeconds;
    Settings.bEnableVoiceInput = bEnableVoiceInput;
    Settings.bEnableVoiceBargeIn = bEnableVoiceBargeIn;
    Settings.bEnableStreamingStt = bEnableStreamingStt;

    TWeakObjectPtr<UPromptMotionRuntimeComponent> WeakThis(this);
    FPromptMotionVoiceInputEvents Events;
    Events.IsVoiceBlocked = [WeakThis]()
    {
        const UPromptMotionRuntimeComponent* Self = WeakThis.Get();
        return Self
            ? Self->ShouldIgnoreVoiceForTtsCooldown() || Self->IsVoiceSubmissionBlocked()
            : true;
    };
    Events.IsPlaybackActive = [WeakThis]()
    {
        const UPromptMotionRuntimeComponent* Self = WeakThis.Get();
        return Self && (Self->bLipSyncActive || (Self->SpeechPlaybackController.IsValid() && Self->SpeechPlaybackController->IsPlaybackActive()));
    };
    Events.OnBargeInRequested = [WeakThis]()
    {
        if (UPromptMotionRuntimeComponent* Self = WeakThis.Get())
            Self->CancelActiveTts();
    };
    Events.OnSpeechStarted = [WeakThis]()
    {
        if (UPromptMotionRuntimeComponent* Self = WeakThis.Get())
            Self->SetVoiceStatus(EPromptMotionVoiceStatus::UserSpeaking);
    };
    Events.OnTranscribing = [WeakThis]()
    {
        if (UPromptMotionRuntimeComponent* Self = WeakThis.Get())
        {
            Self->ApplyFacePreset(TEXT("thinking"), 0.45f);
            Self->SetVoiceStatus(EPromptMotionVoiceStatus::Transcribing);
        }
    };
    Events.OnError = [WeakThis]()
    {
        if (UPromptMotionRuntimeComponent* Self = WeakThis.Get())
        {
            Self->ApplyFacePreset(TEXT("uncertain"), 0.35f);
            Self->SetVoiceStatus(EPromptMotionVoiceStatus::Error);
            Self->SetComponentTickEnabled(true);
        }
    };
    Events.OnTranscriptReady = [WeakThis](const FPromptMotionSttResult& Result, const FPromptMotionVoiceLatencyTrace& Trace)
    {
        UPromptMotionRuntimeComponent* Self = WeakThis.Get();
        if (!Self)
            return;

        Self->LastSttLatencyMs = Result.SttLatencyMs;
        Self->PendingVoiceTrace = Trace;
        Self->bPendingVoiceTrace = true;
        Self->SetVoiceStatus(EPromptMotionVoiceStatus::Thinking);
        Self->SendRuntimeMessage(Result.Text);
    };

    VoiceInputController->Configure(Settings, MoveTemp(Events));
}

void UPromptMotionRuntimeComponent::ConfigureSpeechPlaybackController()
{
    if (!SpeechPlaybackController.IsValid())
        SpeechPlaybackController = MakeShared<FPromptMotionSpeechPlaybackController>();

    FPromptMotionSpeechPlaybackSettings Settings;
    Settings.ServerUrl = ServerUrl;
    Settings.bEnableTts = bEnableTts;

    TWeakObjectPtr<UPromptMotionRuntimeComponent> WeakThis(this);
    FPromptMotionSpeechPlaybackEvents Events;
    Events.OnTtsDisabled = [WeakThis](const FString& RequestId)
    {
        if (UPromptMotionRuntimeComponent* Self = WeakThis.Get())
        {
            if (Self->ActiveVoiceTrace.RequestId == Self->ParseUnrealRequestId(RequestId))
                Self->AppendVoiceLatencyCsv(nullptr, TEXT("tts_disabled"));
        }
    };
    Events.OnTtsRequestStarted = [WeakThis](const FString& RequestId)
    {
        if (UPromptMotionRuntimeComponent* Self = WeakThis.Get())
        {
            Self->ActiveTtsRequestId = RequestId;
            if (Self->ActiveVoiceTrace.RequestId == Self->ParseUnrealRequestId(RequestId))
                Self->ActiveVoiceTrace.TtsRequestSentWorldSeconds = FPlatformTime::Seconds();
        }
    };
    Events.OnTtsFailed = [WeakThis](const FString& RequestId)
    {
        if (UPromptMotionRuntimeComponent* Self = WeakThis.Get())
        {
            if (Self->ActiveVoiceTrace.RequestId == Self->ParseUnrealRequestId(RequestId))
                Self->AppendVoiceLatencyCsv(nullptr, TEXT("tts_failed"));
        }
    };
    Events.OnTtsReady = [WeakThis](const FString& RequestId, const FPromptMotionSpeechTimeline&)
    {
        if (UPromptMotionRuntimeComponent* Self = WeakThis.Get())
        {
            if (Self->ActiveVoiceTrace.RequestId == Self->ParseUnrealRequestId(RequestId))
            {
                Self->ActiveVoiceTrace.TtsReadyWorldSeconds = FPlatformTime::Seconds();
                UE_LOG(LogPromptMotion, Log,
                    TEXT("[VoiceLatency] tts_ready request=%s speechEndToTtsReadyMs=%.0f llmReadyToTtsReadyMs=%.0f"),
                    *RequestId,
                    ComputeElapsedMs(Self->ActiveVoiceTrace.SpeechEndWorldSeconds, Self->ActiveVoiceTrace.TtsReadyWorldSeconds),
                    ComputeElapsedMs(Self->ActiveVoiceTrace.LlmReadyWorldSeconds, Self->ActiveVoiceTrace.TtsReadyWorldSeconds));
            }
        }
    };
    Events.OnTimelineReady = [WeakThis](const FString& RequestId, const FPromptMotionSpeechTimeline& Timeline)
    {
        if (UPromptMotionRuntimeComponent* Self = WeakThis.Get())
        {
            if (Self->ActiveTtsRequestId == RequestId)
                Self->StartLipSyncTimeline(Timeline);
        }
    };
    Events.OnAudioStarted = [WeakThis](const FString& RequestId)
    {
        if (UPromptMotionRuntimeComponent* Self = WeakThis.Get())
        {
            Self->SetVoiceStatus(EPromptMotionVoiceStatus::CharacterSpeaking);
            if (Self->ActiveVoiceTrace.RequestId == Self->ParseUnrealRequestId(RequestId))
            {
                Self->ActiveVoiceTrace.AudioPlayStartWorldSeconds = FPlatformTime::Seconds();
                UE_LOG(LogPromptMotion, Log,
                    TEXT("[VoiceLatency] audio_start request=%s speechEndToAudioMs=%.0f sttFinalToAudioMs=%.0f llmReadyToAudioMs=%.0f ttsReadyToAudioMs=%.0f"),
                    *RequestId,
                    ComputeElapsedMs(Self->ActiveVoiceTrace.SpeechEndWorldSeconds, Self->ActiveVoiceTrace.AudioPlayStartWorldSeconds),
                    ComputeElapsedMs(Self->ActiveVoiceTrace.SttReadyWorldSeconds, Self->ActiveVoiceTrace.AudioPlayStartWorldSeconds),
                    ComputeElapsedMs(Self->ActiveVoiceTrace.LlmReadyWorldSeconds, Self->ActiveVoiceTrace.AudioPlayStartWorldSeconds),
                    ComputeElapsedMs(Self->ActiveVoiceTrace.TtsReadyWorldSeconds, Self->ActiveVoiceTrace.AudioPlayStartWorldSeconds));
                Self->AppendVoiceLatencyCsv(nullptr, TEXT("audio_play_start"));
            }
        }
    };

    SpeechPlaybackController->Configure(this, Settings, MoveTemp(Events));
}

bool UPromptMotionRuntimeComponent::RequestMicrophonePermission()
{
#if PLATFORM_ANDROID
    static const FString RecordAudioPermission = TEXT("android.permission.RECORD_AUDIO");
    bMicrophonePermissionGranted = UAndroidPermissionFunctionLibrary::CheckPermission(RecordAudioPermission);
    if (bMicrophonePermissionGranted)
        return true;

    TArray<FString> Permissions;
    Permissions.Add(RecordAudioPermission);
    UAndroidPermissionCallbackProxy* Proxy = UAndroidPermissionFunctionLibrary::AcquirePermissions(Permissions);
    if (Proxy)
        Proxy->OnPermissionsGrantedDynamicDelegate.AddDynamic(this, &UPromptMotionRuntimeComponent::HandleAndroidMicrophonePermissionResult);
    UE_LOG(LogPromptMotion, Warning, TEXT("[Voice] Android RECORD_AUDIO permission requested"));
    return false;
#else
    bMicrophonePermissionGranted = true;
    return true;
#endif
}

bool UPromptMotionRuntimeComponent::HasMicrophonePermission() const
{
    return bMicrophonePermissionGranted;
}

bool UPromptMotionRuntimeComponent::SubmitDebugSttWav(double NowSeconds)
{
    if (bDebugSttInFlight || IsVoiceSubmissionBlocked())
    {
        UE_LOG(LogPromptMotion, Log, TEXT("[STT] Debug WAV submit ignored while voice pipeline is busy: inFlight=%s status=%d"),
            bDebugSttInFlight ? TEXT("true") : TEXT("false"),
            static_cast<int32>(VoiceStatus));
        return false;
    }

    TArray<uint8> WavBytes;
    const FString WavPath = ResolveDebugSttWavPath();
    if (WavPath.IsEmpty() || !FFileHelper::LoadFileToArray(WavBytes, *WavPath) || WavBytes.IsEmpty())
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[STT] Debug WAV load failed: %s"), *DebugSttWavPath);
        ApplyFacePreset(TEXT("uncertain"), 0.35f);
        SetVoiceStatus(EPromptMotionVoiceStatus::Error);
        return false;
    }

    EnsureDebugSttClient();
    if (!DebugSttClient.IsValid())
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[STT] Debug STT client unavailable"));
        SetVoiceStatus(EPromptMotionVoiceStatus::Error);
        return false;
    }

    FPromptMotionVoiceLatencyTrace Trace;
    Trace.InputMode = TEXT("debug_wav");
    Trace.SpeechStartWorldSeconds = NowSeconds;
    Trace.SpeechEndWorldSeconds = NowSeconds;
    Trace.SttRequestSentWorldSeconds = NowSeconds;

    ApplyFacePreset(TEXT("thinking"), 0.45f);
    SetVoiceStatus(EPromptMotionVoiceStatus::Transcribing);
    bDebugSttInFlight = true;

    TWeakObjectPtr<UPromptMotionRuntimeComponent> WeakThis(this);
    DebugSttClient->TranscribeWav(
        WavBytes,
        SttLanguage,
        [WeakThis, Trace = MoveTemp(Trace), WavPath](bool bSuccess, const FPromptMotionSttResult& Result) mutable
        {
            UPromptMotionRuntimeComponent* Self = WeakThis.Get();
            if (!Self)
                return;

            if (!bSuccess || Result.Text.IsEmpty())
            {
                Self->bDebugSttInFlight = false;
                UE_LOG(LogPromptMotion, Warning, TEXT("[STT] Debug WAV transcribe failed: %s"), *WavPath);
                Self->ApplyFacePreset(TEXT("uncertain"), 0.35f);
                Self->SetVoiceStatus(EPromptMotionVoiceStatus::Error);
                return;
            }

            Trace.SttReadyWorldSeconds = FPlatformTime::Seconds();
            Trace.Transcript = Result.Text;
            Trace.Provider = Result.Provider;
            Trace.Model = Result.Model;
            Trace.SttProviderLatencyMs = Result.SttLatencyMs;

            Self->LastSttLatencyMs = Result.SttLatencyMs;
            Self->bDebugSttInFlight = false;
            Self->PendingVoiceTrace = Trace;
            Self->bPendingVoiceTrace = true;
            Self->SetVoiceStatus(EPromptMotionVoiceStatus::Thinking);

            UE_LOG(LogPromptMotion, Log, TEXT("[STT] Debug WAV transcribed: \"%s\" provider=%s/%s latency=%dms path=%s"),
                *Result.Text, *Result.Provider, *Result.Model, Result.SttLatencyMs, *WavPath);
            Self->SendRuntimeMessage(Result.Text);
        });

    return true;
}

FString UPromptMotionRuntimeComponent::ResolveDebugSttWavPath() const
{
    if (DebugSttWavPath.IsEmpty())
        return FString();

    FString Path = DebugSttWavPath;
    FPaths::NormalizeFilename(Path);
    if (FPaths::FileExists(Path))
        return FPaths::ConvertRelativePathToFull(Path);

    if (FPaths::IsRelative(Path))
    {
        const FString ProjectRelative = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir(), Path);
        if (FPaths::FileExists(ProjectRelative))
            return ProjectRelative;

        const FString RootRelative = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(), TEXT("../../"), Path));
        if (FPaths::FileExists(RootRelative))
            return RootRelative;

        const FString FileName = FPaths::GetCleanFilename(Path);
        FString SearchRoot = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir());
        for (int32 Depth = 0; Depth < 5; ++Depth)
        {
            const FString Candidate = FPaths::Combine(SearchRoot, TEXT("Build/reports/stt_smoke"), FileName);
            if (FPaths::FileExists(Candidate))
                return Candidate;
            SearchRoot = FPaths::ConvertRelativePathToFull(FPaths::Combine(SearchRoot, TEXT("..")));
        }
    }

    return FPaths::ConvertRelativePathToFull(Path);
}

void UPromptMotionRuntimeComponent::EnsureDebugSttClient()
{
    const FString Normalized = ServerUrl.TrimEnd();
    if (DebugSttClient.IsValid() && CachedDebugSttBaseUrl == Normalized)
        return;

    CachedDebugSttBaseUrl = Normalized;
    DebugSttClient = MakeUnique<FPromptMotionSttClient>(CachedDebugSttBaseUrl);
}

void UPromptMotionRuntimeComponent::HandleAndroidMicrophonePermissionResult(
    const TArray<FString>& Permissions,
    const TArray<bool>& GrantResults)
{
    bMicrophonePermissionGranted = false;
    for (int32 Index = 0; Index < Permissions.Num(); ++Index)
    {
        if (Permissions[Index] == TEXT("android.permission.RECORD_AUDIO"))
        {
            bMicrophonePermissionGranted = GrantResults.IsValidIndex(Index) && GrantResults[Index];
            break;
        }
    }

    UE_LOG(LogPromptMotion, Log, TEXT("[Voice] Android RECORD_AUDIO permission granted=%s"),
        bMicrophonePermissionGranted ? TEXT("true") : TEXT("false"));
    SetVoiceStatus(bMicrophonePermissionGranted ? EPromptMotionVoiceStatus::Idle : EPromptMotionVoiceStatus::Error);
}

void UPromptMotionRuntimeComponent::SetVoiceStatus(EPromptMotionVoiceStatus NewStatus)
{
    if (VoiceStatus == NewStatus)
        return;

    VoiceStatus = NewStatus;
    if (NewStatus == EPromptMotionVoiceStatus::Error)
        VoiceErrorStartedWorldSeconds = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
    OnVoiceStatusChanged.Broadcast(NewStatus);
}

void UPromptMotionRuntimeComponent::AttachVoiceTraceToRequest(int32 RequestId, double LlmRequestSentSeconds)
{
    if (!bPendingVoiceTrace)
        return;

    ActiveVoiceTrace = PendingVoiceTrace;
    ActiveVoiceTrace.RequestId = RequestId;
    ActiveVoiceTrace.LlmRequestSentWorldSeconds = LlmRequestSentSeconds;
    UE_LOG(LogPromptMotion, Log,
        TEXT("[VoiceLatency] llm_request_sent request=%d speechEndToLlmSendMs=%.0f sttFinalToLlmSendMs=%.0f transcript=\"%s\""),
        RequestId,
        ComputeElapsedMs(ActiveVoiceTrace.SpeechEndWorldSeconds, ActiveVoiceTrace.LlmRequestSentWorldSeconds),
        ComputeElapsedMs(ActiveVoiceTrace.SttReadyWorldSeconds, ActiveVoiceTrace.LlmRequestSentWorldSeconds),
        *ActiveVoiceTrace.Transcript);
    bPendingVoiceTrace = false;
}

bool UPromptMotionRuntimeComponent::ShouldIgnoreVoiceForTtsCooldown() const
{
    const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
    const bool bTtsPlaying = bLipSyncActive || (SpeechPlaybackController.IsValid() && SpeechPlaybackController->IsPlaybackActive());
    return bTtsPlaying || (Now - LastTtsStopWorldSeconds) < VoiceTtsCooldownSeconds;
}

bool UPromptMotionRuntimeComponent::IsVoiceSubmissionBlocked() const
{
    if (bDebugSttInFlight)
        return true;
    if (VoiceInputController.IsValid() && VoiceInputController->IsSttInFlight())
        return true;

    return VoiceStatus == EPromptMotionVoiceStatus::Transcribing
        || VoiceStatus == EPromptMotionVoiceStatus::Thinking;
}

bool UPromptMotionRuntimeComponent::IsVoiceInputActive() const
{
    return VoiceInputController.IsValid()
        && (VoiceInputController->IsPushToTalkActive() || VoiceInputController->IsVadEnabled());
}

void UPromptMotionRuntimeComponent::FlushPendingRealtimeRequests()
{
    if (!RealtimeClient.IsValid() || !RealtimeClient->IsConnected() || PendingRealtimeRequests.IsEmpty())
    {
        return;
    }

    TArray<FPendingRealtimeRequest> Requests = MoveTemp(PendingRealtimeRequests);
    for (const FPendingRealtimeRequest& Request : Requests)
    {
        SendRuntimeMessageWithWebSocket(Request.Message, Request.SceneContext, Request.RequestId);
    }
}

void UPromptMotionRuntimeComponent::FallbackPendingRealtimeRequests(const FString& Reason)
{
    if (PendingRealtimeRequests.IsEmpty())
    {
        return;
    }

    TArray<FPendingRealtimeRequest> Requests = MoveTemp(PendingRealtimeRequests);
    for (const FPendingRealtimeRequest& Request : Requests)
    {
        UE_LOG(LogPromptMotion, Warning,
            TEXT("[PromptMotion] WS pending request #%d falling back to HTTP: %s"),
            Request.RequestId, *Reason);
        SendRuntimeMessageWithHttp(Request.Message, Request.SceneContext, Request.RequestId);
    }
}

bool UPromptMotionRuntimeComponent::IsStaleRealtimeRequest(const FString& RequestId) const
{
    return !ActiveRealtimeRequestId.IsEmpty() && RequestId != ActiveRealtimeRequestId;
}

int32 UPromptMotionRuntimeComponent::ParseUnrealRequestId(const FString& RequestId) const
{
    FString Numeric = RequestId;
    Numeric.RemoveFromStart(TEXT("ue_"));
    return FCString::Atoi(*Numeric);
}

void UPromptMotionRuntimeComponent::CancelActiveTts()
{
    StopLipSyncTimeline();
    ActiveTtsRequestId.Empty();
    if (SpeechPlaybackController.IsValid())
        SpeechPlaybackController->Cancel();
    LastTtsStopWorldSeconds = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
}

void UPromptMotionRuntimeComponent::StartTtsForResponse(
    const FString& LlmRequestId,
    const FString& ReplyText,
    const FString& TtsStyle)
{
    ConfigureSpeechPlaybackController();
    if (!SpeechPlaybackController.IsValid())
        return;
    CancelActiveTts();
    SpeechPlaybackController->Start(LlmRequestId, ReplyText, TtsStyle);
}

void UPromptMotionRuntimeComponent::StartTtsTimelineForResponse(
    const FString& LlmRequestId,
    const FPromptMotionSpeechTimeline& Timeline)
{
    ConfigureSpeechPlaybackController();
    if (!SpeechPlaybackController.IsValid())
        return;
    if (ActiveTtsRequestId != LlmRequestId)
        CancelActiveTts();
    SpeechPlaybackController->UpdateTimeline(LlmRequestId, Timeline);
}

void UPromptMotionRuntimeComponent::StartLipSyncTimeline(const FPromptMotionSpeechTimeline& Timeline)
{
    UWorld* StartWorld = GetWorld();
    if (!StartWorld || Timeline.Visemes.IsEmpty())
        return;

    ActiveSpeechTimeline = Timeline;
    bLipSyncActive = true;
    LipSyncStartWorldSeconds = StartWorld->GetTimeSeconds();
    LastAppliedVisemeIndex = INDEX_NONE;
    LastAppliedVisemeId = INDEX_NONE;
    if (!TargetFaceSettings.IsEmpty())
    {
        InitialWeights = CurrentWeights;
        BlendElapsed = 0.0f;
        bFaceBlendActive = true;
    }
    SetComponentTickEnabled(true);

    UE_LOG(LogPromptMotion, Log, TEXT("[TTS] LipSync timeline started: %.2fs, %d visemes"),
        Timeline.DurationSeconds, Timeline.Visemes.Num());
    // ?§Îîî??Ï¢ÖÎ£å ??LipSync Î¶¨ÏÖã
}

void UPromptMotionRuntimeComponent::UpdateLipSyncFromAudioTime(float AudioSeconds)
{
    if (!bLipSyncActive)
        return;

    if (ActiveSpeechTimeline.DurationSeconds > 0.0f &&
        AudioSeconds >= ActiveSpeechTimeline.DurationSeconds + 0.15f)
    {
        StopLipSyncTimeline();
        return;
    }

    // "hold until next" ??ÎßàÏ?ÎßâÏúºÎ°??úÏûë??viseme???§Ïùå viseme???úÏûë???åÍπåÏßÄ ?†Ï?.
    // ?¨Îùº?¥Îî© ?àÎèÑ??Î∞©ÏãùÍ≥??¨Î¶¨ gap?êÏÑú ResetLipSyncÎ•?Ï¶âÏãú ?∏Ï∂ú?òÏ? ?äÏúºÎØÄÎ°?
    // LipSyncLayer.Update()??smooth interpolation???êÏó∞?§ÎüΩÍ≤??¥Ïñ¥Ïß?
    const TArray<FPromptMotionVisemeEvent>& Visemes = ActiveSpeechTimeline.Visemes;
    int32 CurrentIndex = INDEX_NONE;
    for (int32 i = 0; i < Visemes.Num(); ++i)
    {
        if (Visemes[i].TimeSeconds <= AudioSeconds)
            CurrentIndex = i;
        else
            break; // ?úÍ∞Ñ???ïÎ†¨ Î≥¥Ïû•
    }

    if (CurrentIndex == INDEX_NONE)
        return;

    const FPromptMotionVisemeEvent& Event = Visemes[CurrentIndex];
    float EffectiveWeight = FMath::Clamp(Event.Weight, 0.0f, 1.0f);
    const bool bLastViseme = CurrentIndex == Visemes.Num() - 1;
    const bool bPostLastRelease = bLastViseme && AudioSeconds > Event.TimeSeconds;
    if (bPostLastRelease)
    {
        const float ReleaseSeconds = FMath::Max(0.05f, LipSyncPostLastVisemeReleaseSeconds);
        const float ReleaseAlpha = FMath::Clamp((AudioSeconds - Event.TimeSeconds) / ReleaseSeconds, 0.0f, 1.0f);
        EffectiveWeight *= 1.0f - ReleaseAlpha;
    }

    if (CurrentIndex == LastAppliedVisemeIndex && !bPostLastRelease)
        return;

    USkeletalMeshComponent* Mesh = ResolveTargetMesh();
    if (!Mesh)
    {
        StopLipSyncTimeline();
        return;
    }

    LipSyncLayer.ApplyViseme(Event.VisemeId, EffectiveWeight, Mesh);
    LastAppliedVisemeIndex = CurrentIndex;
    LastAppliedVisemeId = Event.VisemeId;
}

void UPromptMotionRuntimeComponent::StopLipSyncTimeline()
{
    const bool bWasLipSyncActive = bLipSyncActive;
    if (USkeletalMeshComponent* Mesh = ResolveTargetMesh())
    {
        LipSyncLayer.ResetLipSync(Mesh);
    }

    ActiveSpeechTimeline = FPromptMotionSpeechTimeline{};
    bLipSyncActive = false;
    LipSyncStartWorldSeconds = 0.0;
    if (bWasLipSyncActive)
    {
        LastTtsStopWorldSeconds = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
        SetVoiceStatus(VoiceInputController.IsValid() && VoiceInputController->IsVadEnabled()
            ? EPromptMotionVoiceStatus::Listening
            : EPromptMotionVoiceStatus::Cooldown);
        SetComponentTickEnabled(true);
    }
    LastAppliedVisemeIndex = INDEX_NONE;
    LastAppliedVisemeId = INDEX_NONE;
    if (!TargetFaceSettings.IsEmpty())
    {
        InitialWeights = CurrentWeights;
        BlendElapsed = 0.0f;
        bFaceBlendActive = true;
        SetComponentTickEnabled(true);
    }
}

void UPromptMotionRuntimeComponent::AppendLatencyCsv(
    int32 RequestId,
    const FString& Message,
    const FPromptMotionRuntimeResponse& Response,
    double RequestStartTime,
    double ResponseReceivedTime,
    double FirstVisibleReactionMs) const
{
    if (!bEnableLatencyCsv)
    {
        return;
    }

    FPromptMotionRuntimeLatencyRecord Record;
    Record.SessionId = SessionId;
    Record.Message = Message;
    Record.DefaultTechProfile = LatencyTechProfile;
    Record.Response = &Response;
    Record.RequestId = RequestId;
    Record.LastSttLatencyMs = LastSttLatencyMs;
    Record.RequestStartTime = RequestStartTime;
    Record.ResponseReceivedTime = ResponseReceivedTime;
    Record.FirstVisibleReactionMs = FirstVisibleReactionMs;
    FPromptMotionLatencyLogger::AppendRuntimeLatencyCsv(Record);
    LastSttLatencyMs = -1;
}

void UPromptMotionRuntimeComponent::AppendVoiceLatencyCsv(
    const FPromptMotionRuntimeResponse* Response,
    const FString& Notes) const
{
    if (!bEnableLatencyCsv || ActiveVoiceTrace.SpeechStartWorldSeconds <= 0.0)
        return;

    FPromptMotionVoiceLatencyRecord Record;
    Record.SessionId = SessionId;
    Record.Trace = ActiveVoiceTrace;
    Record.Notes = Notes;
    Record.Response = Response;
    FPromptMotionLatencyLogger::AppendVoiceLatencyCsv(Record);
}
