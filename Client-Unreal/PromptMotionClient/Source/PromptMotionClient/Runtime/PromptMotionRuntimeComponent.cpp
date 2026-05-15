#include "PromptMotionRuntimeComponent.h"
#include "PromptMotionApiClient.h"
#include "FacePresetResolver.h"
#include "PromptMotionLog.h"
#include "Components/SkeletalMeshComponent.h"

DEFINE_LOG_CATEGORY(LogPromptMotion);

UPromptMotionRuntimeComponent::UPromptMotionRuntimeComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void UPromptMotionRuntimeComponent::BeginPlay()
{
    Super::BeginPlay();
    EnsureApiClient();
}

void UPromptMotionRuntimeComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
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
    EnsureApiClient();

    // [D] 요청 즉시 Thinking 표정 적용 — 서버 응답 대기 중 캐릭터가 멈춰 보이지 않도록
    ApplyFacePreset(TEXT("thinking"), 0.45f);

    // [C] 요청 ID 발급 — 응답 수신 시 stale 여부 판별에 사용
    const int32 ThisRequestId = RequestIdCounter.Increment();

    // [B] 요청 시각 기록 — round-trip latency 측정용
    const double RequestStartTime = FPlatformTime::Seconds();

    UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] Request #%d → %s | \"%s\""),
        ThisRequestId, *ServerUrl, *Message);

    TWeakObjectPtr<UPromptMotionRuntimeComponent> WeakThis(this);

    ApiClient->SendRuntimeRequest(
        SessionId, CharacterId, Message, SceneContext,
        [WeakThis, ThisRequestId, RequestStartTime](const FPromptMotionRuntimeResponse& Response)
        {
            UPromptMotionRuntimeComponent* Self = WeakThis.Get();
            if (!Self)
                return;

            // [B] Round-trip latency 로그
            const double ElapsedMs = (FPlatformTime::Seconds() - RequestStartTime) * 1000.0;

            // [C] Stale 응답 무시 — 더 새로운 요청이 이미 발송된 경우
            const int32 CurrentId = Self->RequestIdCounter.GetValue();
            if (ThisRequestId != CurrentId)
            {
                UE_LOG(LogPromptMotion, Log,
                    TEXT("[PromptMotion] Request #%d stale (current=#%d), %.0fms — discarded"),
                    ThisRequestId, CurrentId, ElapsedMs);
                return;
            }

            if (Response.bSuccess)
            {
                Self->LastReply    = Response.Reply;
                Self->LastBehavior = Response.Behavior;

                UE_LOG(LogPromptMotion, Log,
                    TEXT("[PromptMotion] Request #%d OK | %.0fms\n")
                    TEXT("  reply      : %s\n")
                    TEXT("  emotion    : %s (intensity=%.2f)\n")
                    TEXT("  intent     : %s (confidence=%.2f)\n")
                    TEXT("  gestureKey : %s | headMotion : %s | ttsStyle : %s"),
                    ThisRequestId, ElapsedMs,
                    *Response.Reply,
                    *Response.Behavior.Emotion,   Response.Behavior.Intensity,
                    *Response.Behavior.Intent,    Response.Behavior.Confidence,
                    *Response.Behavior.GestureKey,
                    *Response.Behavior.HeadMotion,
                    *Response.Behavior.TtsStyle
                );

                // Behavior JSON → Morph Target 자동 적용
                Self->ApplyFacePreset(Response.Behavior.Emotion, Response.Behavior.Intensity);
            }
            else
            {
                UE_LOG(LogPromptMotion, Warning,
                    TEXT("[PromptMotion] Request #%d FAILED | %.0fms — %s"),
                    ThisRequestId, ElapsedMs, *Response.ErrorMessage);

                // Reset the immediate thinking reaction so failures/timeouts do not leave the face stuck.
                Self->ApplyFacePreset(TEXT("neutral"), 0.0f);
            }

            Self->OnRuntimeResponseReceived.Broadcast(Response);
        }
    );
}

void UPromptMotionRuntimeComponent::ApplyFacePreset(const FString& Emotion, float Intensity)
{
    USkeletalMeshComponent* Mesh = ResolveTargetMesh();
    if (!Mesh)
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[PromptMotion] ApplyFacePreset: TargetMesh not found on '%s'"),
            GetOwner() ? *GetOwner()->GetName() : TEXT("null"));
        return;
    }

    const TMap<FName, float> Weights = FFacePresetResolver::Resolve(Emotion, Intensity);

    for (const auto& Pair : Weights)
    {
        Mesh->SetMorphTarget(Pair.Key, Pair.Value);
    }

    UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] FacePreset applied — emotion=%s intensity=%.2f morphs=%d"),
        *Emotion, Intensity, Weights.Num());
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

void UPromptMotionRuntimeComponent::EnsureApiClient()
{
    if (!ApiClient.IsValid() || CachedBaseUrl != ServerUrl)
    {
        CachedBaseUrl = ServerUrl;
        ApiClient = MakeUnique<FPromptMotionApiClient>(ServerUrl);
    }
}
