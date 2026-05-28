#pragma once

#include "CoreMinimal.h"
#include "PromptMotionTypes.h"

class FJsonObject;

/**
 * PromptMotionLab Python 서버와 통신하는 HTTP 클라이언트.
 * UObject 아님 — 순수 C++ 클래스.
 *
 * 사용처: UPromptMotionRuntimeComponent가 소유.
 */
class FPromptMotionApiClient
{
public:
    explicit FPromptMotionApiClient(const FString& InBaseUrl);

    /**
     * POST /api/runtime/respond 호출.
     * 응답은 게임 스레드에서 OnComplete 콜백으로 전달.
     */
    void SendRuntimeRequest(
        const FString& SessionId,
        const FString& CharacterId,
        const FString& Message,
        const FPromptMotionSceneContext& SceneContext,
        TFunction<void(const FPromptMotionRuntimeResponse&)> OnComplete
    );

    void SubmitTurnAsyncRequest(
        const FString& SessionId,
        const FString& CharacterId,
        const FString& Message,
        const FPromptMotionSceneContext& SceneContext,
        TFunction<void(const FPromptMotionTurnAsyncAccepted&)> OnComplete
    );

    void PollTurnAsyncJob(
        const FString& TurnJobId,
        TFunction<void(const FPromptMotionTurnAsyncJob&)> OnComplete
    );

private:
    FString BaseUrl;

    static FPromptMotionRuntimeResponse ParseResponse(const FString& JsonBody);
    static FPromptMotionTurnAsyncAccepted ParseTurnAccepted(const FString& JsonBody);
    static FPromptMotionTurnAsyncJob ParseTurnJob(const FString& JsonBody);
    static void ParseBehaviorObject(const TSharedPtr<FJsonObject>& BehaviorObj, FPromptMotionBehavior& OutBehavior);
    static void ParseMetadataObject(const TSharedPtr<FJsonObject>& MetadataObj, FPromptMotionRuntimeMetadata& OutMetadata);
    static void ParseSpeechTimelineObject(const TSharedPtr<FJsonObject>& TimelineObj, FPromptMotionSpeechTimeline& OutTimeline);
};
