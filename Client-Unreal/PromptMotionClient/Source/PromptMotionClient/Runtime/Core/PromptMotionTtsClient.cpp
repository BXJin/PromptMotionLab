#include "PromptMotionTtsClient.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "PromptMotionLog.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

FPromptMotionTtsClient::FPromptMotionTtsClient(const FString& InBaseUrl)
    : BaseUrl(InBaseUrl)
{
}

void FPromptMotionTtsClient::Synthesize(
    const FString& Text,
    const FString& TtsStyle,
    TFunction<void(bool bSuccess, const FPromptMotionSpeechTimeline& Timeline)> OnComplete)
{
    TSharedRef<TFunction<void(bool, const FPromptMotionSpeechTimeline&)>> Callback =
        MakeShared<TFunction<void(bool, const FPromptMotionSpeechTimeline&)>>(MoveTemp(OnComplete));
    SynthesizeAttempt(Text, TtsStyle, 0, Callback);
}

void FPromptMotionTtsClient::SynthesizeAttempt(
    const FString& Text,
    const FString& TtsStyle,
    int32 Attempt,
    TSharedRef<TFunction<void(bool, const FPromptMotionSpeechTimeline&)>> Callback)
{
    constexpr int32 MaxAttempts = 2;
    TSharedPtr<FJsonObject> Body = MakeShared<FJsonObject>();
    Body->SetStringField(TEXT("text"), Text);
    Body->SetStringField(TEXT("ttsStyle"), TtsStyle);

    FString BodyStr;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&BodyStr);
    FJsonSerializer::Serialize(Body.ToSharedRef(), Writer);

    TSharedRef<IHttpRequest> Req = FHttpModule::Get().CreateRequest();
    Req->SetURL(BaseUrl + TEXT("/api/runtime/tts/synthesize"));
    Req->SetVerb(TEXT("POST"));
    Req->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    Req->SetContentAsString(BodyStr);
    Req->SetTimeout(15.0f);

    Req->OnProcessRequestComplete().BindLambda(
        [this, Text, TtsStyle, Attempt, Callback](FHttpRequestPtr, FHttpResponsePtr Response, bool bConnected)
        {
            const bool bRetryableHttp = Response.IsValid() &&
                (Response->GetResponseCode() == 408 || Response->GetResponseCode() == 429 || Response->GetResponseCode() >= 500);
            if (!bConnected || !Response.IsValid() || bRetryableHttp)
            {
                const int32 Code = Response.IsValid() ? Response->GetResponseCode() : -1;
                UE_LOG(LogPromptMotion, Warning, TEXT("[TTS] Synthesize failed code=%d attempt=%d"), Code, Attempt + 1);
                if (Attempt + 1 < MaxAttempts)
                {
                    SynthesizeAttempt(Text, TtsStyle, Attempt + 1, Callback);
                    return;
                }
                (*Callback)(false, FPromptMotionSpeechTimeline{});
                return;
            }
            if (Response->GetResponseCode() != 200)
            {
                UE_LOG(LogPromptMotion, Warning, TEXT("[TTS] Synthesize HTTP %d"), Response->GetResponseCode());
                (*Callback)(false, FPromptMotionSpeechTimeline{});
                return;
            }

            FPromptMotionSpeechTimeline Timeline = ParseSpeechTimeline(Response->GetContentAsString());
            (*Callback)(!Timeline.UtteranceId.IsEmpty(), Timeline);
        });

    Req->ProcessRequest();
}

void FPromptMotionTtsClient::DownloadAudio(
    const FString& RelativeUrl,
    TFunction<void(bool bSuccess, TArray<uint8> WavBytes)> OnComplete)
{
    TSharedRef<TFunction<void(bool, TArray<uint8>)>> Callback =
        MakeShared<TFunction<void(bool, TArray<uint8>)>>(MoveTemp(OnComplete));
    DownloadAudioAttempt(RelativeUrl, 0, Callback);
}

void FPromptMotionTtsClient::DownloadAudioAttempt(
    const FString& RelativeUrl,
    int32 Attempt,
    TSharedRef<TFunction<void(bool, TArray<uint8>)>> Callback)
{
    constexpr int32 MaxAttempts = 2;
    TSharedRef<IHttpRequest> Req = FHttpModule::Get().CreateRequest();
    Req->SetURL(BaseUrl + RelativeUrl);
    Req->SetVerb(TEXT("GET"));
    Req->SetTimeout(20.0f);

    Req->OnProcessRequestComplete().BindLambda(
        [this, Callback, RelativeUrl, Attempt](FHttpRequestPtr, FHttpResponsePtr Response, bool bConnected)
        {
            const bool bRetryableHttp = Response.IsValid() &&
                (Response->GetResponseCode() == 408 || Response->GetResponseCode() == 429 || Response->GetResponseCode() >= 500);
            if (!bConnected || !Response.IsValid() || bRetryableHttp)
            {
                const int32 Code = Response.IsValid() ? Response->GetResponseCode() : -1;
                UE_LOG(LogPromptMotion, Warning, TEXT("[TTS] WAV download failed code=%d attempt=%d url=%s"), Code, Attempt + 1, *RelativeUrl);
                if (Attempt + 1 < MaxAttempts)
                {
                    DownloadAudioAttempt(RelativeUrl, Attempt + 1, Callback);
                    return;
                }
                (*Callback)(false, TArray<uint8>{});
                return;
            }
            if (Response->GetResponseCode() != 200)
            {
                UE_LOG(LogPromptMotion, Warning, TEXT("[TTS] WAV HTTP %d: %s"), Response->GetResponseCode(), *RelativeUrl);
                (*Callback)(false, TArray<uint8>{});
                return;
            }
            (*Callback)(true, Response->GetContent());
        });

    Req->ProcessRequest();
}
FPromptMotionSpeechTimeline FPromptMotionTtsClient::ParseSpeechTimeline(const FString& JsonBody)
{
    FPromptMotionSpeechTimeline Result;

    TSharedPtr<FJsonObject> Root;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonBody);
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[TTS] SpeechTimeline JSON ?뚯떛 ?ㅽ뙣"));
        return Result;
    }

    // speechTimeline 媛앹껜
    const TSharedPtr<FJsonObject>* TimelineObj;
    if (!Root->TryGetObjectField(TEXT("speechTimeline"), TimelineObj) || !TimelineObj)
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[TTS] speechTimeline ?꾨뱶 ?놁쓬"));
        return Result;
    }

    (*TimelineObj)->TryGetStringField(TEXT("utteranceId"), Result.UtteranceId);

    // audio 媛앹껜
    const TSharedPtr<FJsonObject>* AudioObj;
    if ((*TimelineObj)->TryGetObjectField(TEXT("audio"), AudioObj) && AudioObj)
    {
        (*AudioObj)->TryGetStringField(TEXT("url"), Result.Audio.Url);
        (*AudioObj)->TryGetStringField(TEXT("format"), Result.Audio.Format);
        Result.AudioUrl = Result.Audio.Url;

        double DurTemp = 0.0;
        if ((*AudioObj)->TryGetNumberField(TEXT("durationSeconds"), DurTemp))
        {
            Result.Audio.DurationSeconds = static_cast<float>(DurTemp);
            Result.DurationSeconds = static_cast<float>(DurTemp);
        }
    }

    (*TimelineObj)->TryGetStringField(TEXT("provider"), Result.Provider);
    (*TimelineObj)->TryGetStringField(TEXT("model"), Result.Model);
    int32 LatencyMs = -1;
    if ((*TimelineObj)->TryGetNumberField(TEXT("ttsLatencyMs"), LatencyMs))
        Result.TtsLatencyMs = LatencyMs;

    // visemes 諛곗뿴
    const TArray<TSharedPtr<FJsonValue>>* VisemesArr;
    if ((*TimelineObj)->TryGetArrayField(TEXT("visemes"), VisemesArr))
    {
        Result.Visemes.Reserve(VisemesArr->Num());
        for (const TSharedPtr<FJsonValue>& Item : *VisemesArr)
        {
            const TSharedPtr<FJsonObject>* VisObj;
            if (!Item->TryGetObject(VisObj) || !VisObj)
                continue;

                // ?쒕쾭 SpeechViseme: { "time": seconds, "id": int, "weight": float }
            FPromptMotionVisemeEvent Event;
            int32 VisId = 0;
            double TimeSeconds = 0.0;
            double Weight = 1.0;

            (*VisObj)->TryGetNumberField(TEXT("id"), VisId);
            (*VisObj)->TryGetNumberField(TEXT("time"), TimeSeconds);
            (*VisObj)->TryGetNumberField(TEXT("weight"), Weight);

            Event.VisemeId = VisId;
            Event.TimeSeconds = static_cast<float>(TimeSeconds);
            Event.OffsetMs = static_cast<float>(TimeSeconds * 1000.0); // 珥???ms
            Event.Weight = static_cast<float>(Weight);
            Result.Visemes.Add(Event);
        }
    }

    UE_LOG(LogPromptMotion, Log, TEXT("[TTS] Timeline parsed ??utteranceId=%s duration=%.2fs visemes=%d"),
        *Result.UtteranceId, Result.DurationSeconds, Result.Visemes.Num());

    return Result;
}
