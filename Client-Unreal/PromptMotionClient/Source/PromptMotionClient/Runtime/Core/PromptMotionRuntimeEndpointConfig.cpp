#include "PromptMotionRuntimeEndpointConfig.h"

#include "Misc/ConfigCacheIni.h"

namespace
{
constexpr TCHAR RuntimeSection[] = TEXT("PromptMotion.Runtime");

bool IsUsableWebSocketUrl(const FString& Url)
{
    return Url.StartsWith(TEXT("ws://")) || Url.StartsWith(TEXT("wss://")) || Url.StartsWith(TEXT("wss+insecure://"));
}

FString BuildWebSocketUrlFromServerUrl(const FString& ServerUrl, const TCHAR* Path)
{
    FString Url = ServerUrl.TrimEnd();
    if (Url.StartsWith(TEXT("https://")))
        Url = TEXT("wss://") + Url.RightChop(8);
    else if (Url.StartsWith(TEXT("http://")))
        Url = TEXT("ws://") + Url.RightChop(7);
    else
        return FString();

    Url.RemoveFromEnd(TEXT("/"));
    return Url + Path;
}

void ReadBool(const TCHAR* Section, const TCHAR* Key, bool& Value)
{
    bool LoadedValue = Value;
    if (GConfig && GConfig->GetBool(Section, Key, LoadedValue, GGameIni))
        Value = LoadedValue;
}

void ReadFloat(const TCHAR* Section, const TCHAR* Key, float& Value)
{
    float LoadedValue = Value;
    if (GConfig && GConfig->GetFloat(Section, Key, LoadedValue, GGameIni))
        Value = LoadedValue;
}

void ReadString(const TCHAR* Section, const TCHAR* Key, FString& Value)
{
    FString LoadedValue;
    if (GConfig && GConfig->GetString(Section, Key, LoadedValue, GGameIni) && !LoadedValue.IsEmpty())
        Value = LoadedValue;
}
}

bool FPromptMotionRuntimeEndpointConfig::LoadFromConfig(const FString& ProfileOverride)
{
    if (!GConfig)
        return false;

    ReadString(RuntimeSection, TEXT("ActiveProfile"), ActiveProfile);
    if (!ProfileOverride.IsEmpty())
        ActiveProfile = ProfileOverride;

    const FString ProfileSection = GetProfileSectionName(ActiveProfile);
    ReadString(*ProfileSection, TEXT("ServerUrl"), ServerUrl);
    ReadString(*ProfileSection, TEXT("RuntimeWebSocketUrl"), RuntimeWebSocketUrl);
    ReadString(*ProfileSection, TEXT("StreamingSttWebSocketUrl"), StreamingSttWebSocketUrl);
    ReadBool(*ProfileSection, TEXT("bUseRealtimeWebSocket"), bUseRealtimeWebSocket);
    ReadBool(*ProfileSection, TEXT("bUseAsyncTurnHttp"), bUseAsyncTurnHttp);
    ReadBool(*ProfileSection, TEXT("bEnableStreamingStt"), bEnableStreamingStt);
    ReadFloat(*ProfileSection, TEXT("AsyncTurnPollIntervalSeconds"), AsyncTurnPollIntervalSeconds);
    AsyncTurnPollIntervalSeconds = FMath::Clamp(AsyncTurnPollIntervalSeconds, 0.02f, 1.0f);

    if (!ServerUrl.IsEmpty())
    {
        if (!IsUsableWebSocketUrl(RuntimeWebSocketUrl))
            RuntimeWebSocketUrl = BuildWebSocketUrlFromServerUrl(ServerUrl, TEXT("/ws/runtime"));
        if (!IsUsableWebSocketUrl(StreamingSttWebSocketUrl))
            StreamingSttWebSocketUrl = BuildWebSocketUrlFromServerUrl(ServerUrl, TEXT("/ws/stt"));
    }

    return !ServerUrl.IsEmpty();
}

FString FPromptMotionRuntimeEndpointConfig::GetProfileSectionName(const FString& ProfileName)
{
    return FString::Printf(TEXT("PromptMotion.Runtime.%s"), *ProfileName);
}
