#include "PromptMotionSttClient.h"

#include "Dom/JsonObject.h"
#include "GenericPlatform/GenericPlatformHttp.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "PromptMotionLog.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

FPromptMotionSttClient::FPromptMotionSttClient(const FString& InBaseUrl)
    : BaseUrl(InBaseUrl)
{
}

void FPromptMotionSttClient::TranscribeWav(
    const TArray<uint8>& WavBytes,
    const FString& Language,
    TFunction<void(bool bSuccess, const FPromptMotionSttResult& Result)> OnComplete)
{
    TSharedRef<TFunction<void(bool, const FPromptMotionSttResult&)>> Callback =
        MakeShared<TFunction<void(bool, const FPromptMotionSttResult&)>>(MoveTemp(OnComplete));
    TranscribeWavAttempt(WavBytes, Language, 0, Callback);
}

void FPromptMotionSttClient::TranscribeWavAttempt(
    const TArray<uint8>& WavBytes,
    const FString& Language,
    int32 Attempt,
    TSharedRef<TFunction<void(bool bSuccess, const FPromptMotionSttResult& Result)>> Callback)
{
    constexpr int32 MaxAttempts = 2;
    FString Url = BaseUrl + TEXT("/api/runtime/stt/transcribe");
    if (!Language.IsEmpty())
        Url += FString::Printf(TEXT("?language=%s"), *FGenericPlatformHttp::UrlEncode(Language));

    TSharedRef<IHttpRequest> Req = FHttpModule::Get().CreateRequest();
    Req->SetURL(Url);
    Req->SetVerb(TEXT("POST"));
    Req->SetHeader(TEXT("Content-Type"), TEXT("audio/wav"));
    Req->SetContent(WavBytes);
    Req->SetTimeout(15.0f);

    Req->OnProcessRequestComplete().BindLambda(
        [this, WavBytes, Language, Attempt, Callback](FHttpRequestPtr, FHttpResponsePtr Response, bool bConnected)
        {
            if (!bConnected || !Response.IsValid())
            {
                UE_LOG(LogPromptMotion, Warning, TEXT("[STT] Transcribe failed: no response"));
                if (Attempt + 1 < MaxAttempts)
                {
                    UE_LOG(LogPromptMotion, Warning, TEXT("[STT] Retrying transcribe (%d/%d)"), Attempt + 2, MaxAttempts);
                    TranscribeWavAttempt(WavBytes, Language, Attempt + 1, Callback);
                    return;
                }
                (*Callback)(false, FPromptMotionSttResult{});
                return;
            }
            if (Response->GetResponseCode() != 200)
            {
                UE_LOG(LogPromptMotion, Warning, TEXT("[STT] Transcribe HTTP %d: %s"),
                    Response->GetResponseCode(), *Response->GetContentAsString().Left(200));
                if ((Response->GetResponseCode() == 408 || Response->GetResponseCode() == 429 || Response->GetResponseCode() >= 500) &&
                    Attempt + 1 < MaxAttempts)
                {
                    UE_LOG(LogPromptMotion, Warning, TEXT("[STT] Retrying transcribe after HTTP %d (%d/%d)"),
                        Response->GetResponseCode(), Attempt + 2, MaxAttempts);
                    TranscribeWavAttempt(WavBytes, Language, Attempt + 1, Callback);
                    return;
                }
                (*Callback)(false, FPromptMotionSttResult{});
                return;
            }

            const FPromptMotionSttResult Result = ParseResult(Response->GetContentAsString());
            (*Callback)(!Result.Text.IsEmpty(), Result);
        });

    Req->ProcessRequest();
}

FPromptMotionSttResult FPromptMotionSttClient::ParseResult(const FString& JsonBody)
{
    FPromptMotionSttResult Result;
    TSharedPtr<FJsonObject> Root;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonBody);
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
        return Result;

    Root->TryGetStringField(TEXT("text"), Result.Text);
    Root->TryGetStringField(TEXT("language"), Result.Language);
    Root->TryGetStringField(TEXT("provider"), Result.Provider);
    Root->TryGetStringField(TEXT("model"), Result.Model);

    double Latency = 0.0;
    if (Root->TryGetNumberField(TEXT("sttLatencyMs"), Latency))
        Result.SttLatencyMs = static_cast<int32>(Latency);

    return Result;
}
