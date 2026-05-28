#pragma once

#include "CoreMinimal.h"
#include "PromptMotionTypes.h"

struct FPromptMotionRuntimeLatencyRecord
{
    FString SessionId;
    FString Message;
    FString DefaultTechProfile;
    const FPromptMotionRuntimeResponse* Response = nullptr;
    int32 RequestId = 0;
    int32 LastSttLatencyMs = -1;
    double RequestStartTime = 0.0;
    double ResponseReceivedTime = 0.0;
    double FirstVisibleReactionMs = -1.0;
};

struct FPromptMotionVoiceLatencyTrace
{
    int32 RequestId = 0;
    FString Transcript;
    FString InputMode;
    FString Provider;
    FString Model;
    double SpeechStartWorldSeconds = 0.0;
    double SpeechEndWorldSeconds = 0.0;
    double SttRequestSentWorldSeconds = 0.0;
    double SttReadyWorldSeconds = 0.0;
    double LlmRequestSentWorldSeconds = 0.0;
    double LlmReadyWorldSeconds = 0.0;
    double TtsRequestSentWorldSeconds = 0.0;
    double TtsReadyWorldSeconds = 0.0;
    double AudioPlayStartWorldSeconds = 0.0;
    int32 SttProviderLatencyMs = -1;
};

struct FPromptMotionVoiceLatencyRecord
{
    FString SessionId;
    FPromptMotionVoiceLatencyTrace Trace;
    FString Notes;
    const FPromptMotionRuntimeResponse* Response = nullptr;
};

class FPromptMotionLatencyLogger
{
public:
    static void AppendRuntimeLatencyCsv(const FPromptMotionRuntimeLatencyRecord& Record);
    static void AppendVoiceLatencyCsv(const FPromptMotionVoiceLatencyRecord& Record);

private:
    static FString CsvEscape(const FString& Value);
};
