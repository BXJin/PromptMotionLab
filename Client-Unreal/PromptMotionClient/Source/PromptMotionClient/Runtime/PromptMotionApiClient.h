#pragma once

#include "CoreMinimal.h"
#include "PromptMotionTypes.h"

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

private:
    FString BaseUrl;

    static FPromptMotionRuntimeResponse ParseResponse(const FString& JsonBody);
};
