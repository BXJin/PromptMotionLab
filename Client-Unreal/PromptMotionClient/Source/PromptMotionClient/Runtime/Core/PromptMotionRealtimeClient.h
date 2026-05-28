#pragma once

#include "CoreMinimal.h"
#include "IWebSocket.h"
#include "PromptMotionTypes.h"

class FPromptMotionRealtimeClient
{
public:
    explicit FPromptMotionRealtimeClient(const FString& InWebSocketUrl);
    ~FPromptMotionRealtimeClient();

    void Connect();
    void Close();
    bool IsConnected() const;

    void SendRuntimeRequest(
        const FString& RequestId,
        const FString& SessionId,
        const FString& CharacterId,
        const FString& Message,
        const FPromptMotionSceneContext& SceneContext);

    TFunction<void(const FString& RequestId, const FPromptMotionBehavior& Behavior)> OnReaction;
    TFunction<void(const FString& RequestId, const FPromptMotionRuntimeResponse& Response)> OnFinal;
    TFunction<void(const FString& RequestId, const FString& ErrorMessage)> OnError;
    TFunction<void()> OnConnected;
    TFunction<void(const FString& Reason)> OnClosed;

private:
    FString WebSocketUrl;
    TSharedPtr<IWebSocket> Socket;

    void HandleMessage(const FString& Message);
    void HandleReaction(const FString& RequestId, const TSharedPtr<FJsonObject>& Root);
    void HandleFinal(const FString& RequestId, const TSharedPtr<FJsonObject>& Root);
    void HandleError(const FString& RequestId, const TSharedPtr<FJsonObject>& Root);

    static FPromptMotionBehavior ParseBehavior(const TSharedPtr<FJsonObject>& BehaviorObj);
    static FPromptMotionRuntimeMetadata ParseMetadata(const TSharedPtr<FJsonObject>& MetadataObj);
    static FPromptMotionRuntimeResponse ParseRuntimeResponse(const TSharedPtr<FJsonObject>& ResponseObj);
};
