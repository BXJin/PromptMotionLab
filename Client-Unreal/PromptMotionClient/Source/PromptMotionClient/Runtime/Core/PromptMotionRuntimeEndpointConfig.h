#pragma once

#include "CoreMinimal.h"

struct FPromptMotionRuntimeEndpointConfig
{
    FString ActiveProfile = TEXT("Local");
    FString ServerUrl;
    FString RuntimeWebSocketUrl;
    FString StreamingSttWebSocketUrl;
    bool bUseRealtimeWebSocket = false;
    bool bUseAsyncTurnHttp = true;
    bool bEnableStreamingStt = false;
    float AsyncTurnPollIntervalSeconds = 0.08f;

    bool LoadFromConfig(const FString& ProfileOverride = FString());

private:
    static FString GetProfileSectionName(const FString& ProfileName);
};
