#include "PromptMotionLatencyLogger.h"

#include "HAL/PlatformFileManager.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

FString FPromptMotionLatencyLogger::CsvEscape(const FString& Value)
{
    FString Escaped = Value.Replace(TEXT("\""), TEXT("\"\""));
    return FString::Printf(TEXT("\"%s\""), *Escaped);
}

void FPromptMotionLatencyLogger::AppendRuntimeLatencyCsv(const FPromptMotionRuntimeLatencyRecord& Record)
{
    const FString MetricsDir = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Metrics"));
    IPlatformFile& PlatformFile = FPlatformFileManager::Get().GetPlatformFile();
    PlatformFile.CreateDirectoryTree(*MetricsDir);

    const FString CsvPath = FPaths::Combine(MetricsDir, TEXT("runtime_latency_client.csv"));
    const bool bNeedsHeader = !PlatformFile.FileExists(*CsvPath) || PlatformFile.FileSize(*CsvPath) <= 0;
    const int32 RoundTripMs = static_cast<int32>((Record.ResponseReceivedTime - Record.RequestStartTime) * 1000.0);
    if (!Record.Response)
        return;

    const FPromptMotionRuntimeResponse& Response = *Record.Response;
    const FString RequestIdText = Response.Metadata.RequestId.IsEmpty()
        ? FString::Printf(TEXT("ue_%d"), Record.RequestId)
        : Response.Metadata.RequestId;
    const FString Provider = Response.Metadata.Provider.IsEmpty() ? TEXT("unknown") : Response.Metadata.Provider;
    const FString Model = Response.Metadata.Model.IsEmpty() ? TEXT("unknown") : Response.Metadata.Model;
    const FString TechProfile = Response.Metadata.TechProfile.IsEmpty()
        ? Record.DefaultTechProfile
        : Response.Metadata.TechProfile;
    const FString InputMode = Response.Metadata.InputMode.IsEmpty() ? TEXT("text") : Response.Metadata.InputMode;

    FString Output;
    if (bNeedsHeader)
    {
        Output += TEXT("timestamp,session_id,request_id,input_mode,message_length,provider,model,tech_profile,fallback_used,stt_ms,llm_ms,tts_ms,total_server_ms,unreal_round_trip_ms,first_visible_reaction_ms,first_audio_start_ms,emotion,intent,notes\n");
    }

    TArray<FString> Columns;
    Columns.Add(CsvEscape(FDateTime::UtcNow().ToIso8601()));
    Columns.Add(CsvEscape(Record.SessionId));
    Columns.Add(CsvEscape(RequestIdText));
    Columns.Add(CsvEscape(InputMode));
    Columns.Add(FString::FromInt(Record.Message.Len()));
    Columns.Add(CsvEscape(Provider));
    Columns.Add(CsvEscape(Model));
    Columns.Add(CsvEscape(TechProfile));
    Columns.Add(Response.Metadata.bFallbackUsed ? TEXT("true") : TEXT("false"));
    Columns.Add(Record.LastSttLatencyMs >= 0 ? FString::FromInt(Record.LastSttLatencyMs) : TEXT("-1"));
    Columns.Add(FString::FromInt(Response.Metadata.ProviderLatencyMs));
    Columns.Add(TEXT("-1"));
    Columns.Add(FString::FromInt(Response.Metadata.TotalServerMs));
    Columns.Add(FString::FromInt(RoundTripMs));
    Columns.Add(FString::FromInt(static_cast<int32>(Record.FirstVisibleReactionMs)));
    Columns.Add(TEXT("-1"));
    Columns.Add(CsvEscape(Response.bSuccess ? Response.Behavior.Emotion : TEXT("error")));
    Columns.Add(CsvEscape(Response.bSuccess ? Response.Behavior.Intent : TEXT("error")));
    Columns.Add(CsvEscape(Response.bSuccess ? TEXT("client_response") : Response.ErrorMessage));
    Output += FString::Join(Columns, TEXT(",")) + TEXT("\n");

    FFileHelper::SaveStringToFile(
        Output,
        *CsvPath,
        FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,
        &IFileManager::Get(),
        FILEWRITE_Append);
}

void FPromptMotionLatencyLogger::AppendVoiceLatencyCsv(const FPromptMotionVoiceLatencyRecord& Record)
{
    if (Record.Trace.SpeechStartWorldSeconds <= 0.0)
        return;

    const double T0 = Record.Trace.SpeechStartWorldSeconds;
    auto RelativeMs = [T0](double Timestamp) -> FString
    {
        if (Timestamp <= 0.0)
            return TEXT("-1");
        return FString::FromInt(static_cast<int32>((Timestamp - T0) * 1000.0));
    };

    const FString MetricsDir = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Metrics"));
    IPlatformFile& PlatformFile = FPlatformFileManager::Get().GetPlatformFile();
    PlatformFile.CreateDirectoryTree(*MetricsDir);

    const FString CsvPath = FPaths::Combine(MetricsDir, TEXT("voice_latency_client.csv"));
    const bool bNeedsHeader = !PlatformFile.FileExists(*CsvPath) || PlatformFile.FileSize(*CsvPath) <= 0;

    FString Output;
    if (bNeedsHeader)
    {
        Output += TEXT("timestamp,session_id,request_id,input_mode,transcript_length,stt_provider,stt_model,speech_start_ms,speech_end_ms,stt_request_sent_ms,stt_ready_ms,llm_request_sent_ms,llm_ready_ms,tts_request_sent_ms,tts_ready_ms,audio_play_start_ms,stt_provider_latency_ms,llm_provider_latency_ms,total_server_ms,emotion,intent,notes\n");
    }

    const FPromptMotionRuntimeResponse* Response = Record.Response;
    const FString Emotion = Response && Response->bSuccess ? Response->Behavior.Emotion : TEXT("");
    const FString Intent = Response && Response->bSuccess ? Response->Behavior.Intent : TEXT("");
    const int32 LlmLatency = Response ? Response->Metadata.ProviderLatencyMs : -1;
    const int32 TotalServer = Response ? Response->Metadata.TotalServerMs : -1;

    TArray<FString> Columns;
    Columns.Add(CsvEscape(FDateTime::UtcNow().ToIso8601()));
    Columns.Add(CsvEscape(Record.SessionId));
    Columns.Add(CsvEscape(FString::Printf(TEXT("ue_%d"), Record.Trace.RequestId)));
    Columns.Add(CsvEscape(Record.Trace.InputMode));
    Columns.Add(FString::FromInt(Record.Trace.Transcript.Len()));
    Columns.Add(CsvEscape(Record.Trace.Provider));
    Columns.Add(CsvEscape(Record.Trace.Model));
    Columns.Add(TEXT("0"));
    Columns.Add(RelativeMs(Record.Trace.SpeechEndWorldSeconds));
    Columns.Add(RelativeMs(Record.Trace.SttRequestSentWorldSeconds));
    Columns.Add(RelativeMs(Record.Trace.SttReadyWorldSeconds));
    Columns.Add(RelativeMs(Record.Trace.LlmRequestSentWorldSeconds));
    Columns.Add(RelativeMs(Record.Trace.LlmReadyWorldSeconds));
    Columns.Add(RelativeMs(Record.Trace.TtsRequestSentWorldSeconds));
    Columns.Add(RelativeMs(Record.Trace.TtsReadyWorldSeconds));
    Columns.Add(RelativeMs(Record.Trace.AudioPlayStartWorldSeconds));
    Columns.Add(FString::FromInt(Record.Trace.SttProviderLatencyMs));
    Columns.Add(FString::FromInt(LlmLatency));
    Columns.Add(FString::FromInt(TotalServer));
    Columns.Add(CsvEscape(Emotion));
    Columns.Add(CsvEscape(Intent));
    Columns.Add(CsvEscape(Record.Notes));
    Output += FString::Join(Columns, TEXT(",")) + TEXT("\n");

    FFileHelper::SaveStringToFile(
        Output,
        *CsvPath,
        FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,
        &IFileManager::Get(),
        FILEWRITE_Append);
}
