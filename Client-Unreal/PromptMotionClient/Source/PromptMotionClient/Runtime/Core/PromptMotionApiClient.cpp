#include "PromptMotionApiClient.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

FPromptMotionApiClient::FPromptMotionApiClient(const FString& InBaseUrl)
    : BaseUrl(InBaseUrl)
{
}

void FPromptMotionApiClient::SendRuntimeRequest(
    const FString& SessionId,
    const FString& CharacterId,
    const FString& Message,
    const FPromptMotionSceneContext& SceneContext,
    TFunction<void(const FPromptMotionRuntimeResponse&)> OnComplete)
{
    // --- Build sceneContext JSON ---
    TSharedPtr<FJsonObject> SceneJson = MakeShared<FJsonObject>();
    if (!SceneContext.LocationId.IsEmpty())
        SceneJson->SetStringField(TEXT("locationId"), SceneContext.LocationId);
    if (!SceneContext.FocusedObjectId.IsEmpty())
        SceneJson->SetStringField(TEXT("focusedObjectId"), SceneContext.FocusedObjectId);
    if (!SceneContext.InteractionMode.IsEmpty())
        SceneJson->SetStringField(TEXT("interactionMode"), SceneContext.InteractionMode);

    TArray<TSharedPtr<FJsonValue>> NearbyArray;
    for (const FString& Id : SceneContext.NearbyObjectIds)
        NearbyArray.Add(MakeShared<FJsonValueString>(Id));
    SceneJson->SetArrayField(TEXT("nearbyObjectIds"), NearbyArray);

    // --- Build root request JSON ---
    TSharedPtr<FJsonObject> RequestJson = MakeShared<FJsonObject>();
    RequestJson->SetStringField(TEXT("sessionId"), SessionId);
    RequestJson->SetStringField(TEXT("characterId"), CharacterId);
    RequestJson->SetStringField(TEXT("message"), Message);
    RequestJson->SetObjectField(TEXT("sceneContext"), SceneJson);

    FString RequestBody;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&RequestBody);
    FJsonSerializer::Serialize(RequestJson.ToSharedRef(), Writer);

    // --- HTTP request ---
    auto HttpRequest = FHttpModule::Get().CreateRequest();
    HttpRequest->SetURL(BaseUrl + TEXT("/api/runtime/respond"));
    HttpRequest->SetVerb(TEXT("POST"));
    HttpRequest->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    HttpRequest->SetContentAsString(RequestBody);

    HttpRequest->OnProcessRequestComplete().BindLambda(
        [OnComplete](FHttpRequestPtr /*Req*/, FHttpResponsePtr Response, bool bConnected)
        {
            FPromptMotionRuntimeResponse Result;

            if (!bConnected || !Response.IsValid())
            {
                Result.ErrorMessage = TEXT("HTTP connection failed");
                OnComplete(Result);
                return;
            }

            const int32 Code = Response->GetResponseCode();
            if (Code != 200)
            {
                Result.ErrorMessage = FString::Printf(TEXT("Server returned %d: %s"), Code, *Response->GetContentAsString());
                OnComplete(Result);
                return;
            }

            Result = ParseResponse(Response->GetContentAsString());
            OnComplete(Result);
        }
    );

    HttpRequest->ProcessRequest();
}

void FPromptMotionApiClient::SubmitTurnAsyncRequest(
    const FString& SessionId,
    const FString& CharacterId,
    const FString& Message,
    const FPromptMotionSceneContext& SceneContext,
    TFunction<void(const FPromptMotionTurnAsyncAccepted&)> OnComplete)
{
    TSharedPtr<FJsonObject> SceneJson = MakeShared<FJsonObject>();
    if (!SceneContext.LocationId.IsEmpty())
        SceneJson->SetStringField(TEXT("locationId"), SceneContext.LocationId);
    if (!SceneContext.FocusedObjectId.IsEmpty())
        SceneJson->SetStringField(TEXT("focusedObjectId"), SceneContext.FocusedObjectId);
    if (!SceneContext.InteractionMode.IsEmpty())
        SceneJson->SetStringField(TEXT("interactionMode"), SceneContext.InteractionMode);

    TArray<TSharedPtr<FJsonValue>> NearbyArray;
    for (const FString& Id : SceneContext.NearbyObjectIds)
        NearbyArray.Add(MakeShared<FJsonValueString>(Id));
    SceneJson->SetArrayField(TEXT("nearbyObjectIds"), NearbyArray);

    TSharedPtr<FJsonObject> RequestJson = MakeShared<FJsonObject>();
    RequestJson->SetStringField(TEXT("sessionId"), SessionId);
    RequestJson->SetStringField(TEXT("characterId"), CharacterId);
    RequestJson->SetStringField(TEXT("message"), Message);
    RequestJson->SetObjectField(TEXT("sceneContext"), SceneJson);

    FString RequestBody;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&RequestBody);
    FJsonSerializer::Serialize(RequestJson.ToSharedRef(), Writer);

    TSharedRef<IHttpRequest> HttpRequest = FHttpModule::Get().CreateRequest();
    HttpRequest->SetURL(BaseUrl + TEXT("/api/runtime/turn/async"));
    HttpRequest->SetVerb(TEXT("POST"));
    HttpRequest->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    HttpRequest->SetContentAsString(RequestBody);
    HttpRequest->SetTimeout(10.0f);

    HttpRequest->OnProcessRequestComplete().BindLambda(
        [OnComplete](FHttpRequestPtr, FHttpResponsePtr Response, bool bConnected)
        {
            FPromptMotionTurnAsyncAccepted Result;
            if (!bConnected || !Response.IsValid())
            {
                Result.ErrorMessage = TEXT("HTTP connection failed");
                OnComplete(Result);
                return;
            }

            const int32 Code = Response->GetResponseCode();
            if (Code != 200)
            {
                Result.ErrorMessage = FString::Printf(TEXT("Server returned %d: %s"), Code, *Response->GetContentAsString());
                OnComplete(Result);
                return;
            }

            Result = ParseTurnAccepted(Response->GetContentAsString());
            OnComplete(Result);
        });

    HttpRequest->ProcessRequest();
}

void FPromptMotionApiClient::PollTurnAsyncJob(
    const FString& TurnJobId,
    TFunction<void(const FPromptMotionTurnAsyncJob&)> OnComplete)
{
    TSharedRef<IHttpRequest> HttpRequest = FHttpModule::Get().CreateRequest();
    HttpRequest->SetURL(BaseUrl + TEXT("/api/runtime/turn/jobs/") + TurnJobId);
    HttpRequest->SetVerb(TEXT("GET"));
    HttpRequest->SetTimeout(10.0f);

    HttpRequest->OnProcessRequestComplete().BindLambda(
        [OnComplete](FHttpRequestPtr, FHttpResponsePtr Response, bool bConnected)
        {
            FPromptMotionTurnAsyncJob Result;
            if (!bConnected || !Response.IsValid())
            {
                Result.ErrorMessage = TEXT("HTTP connection failed");
                OnComplete(Result);
                return;
            }

            const int32 Code = Response->GetResponseCode();
            if (Code != 200)
            {
                Result.ErrorMessage = FString::Printf(TEXT("Server returned %d: %s"), Code, *Response->GetContentAsString());
                OnComplete(Result);
                return;
            }

            Result = ParseTurnJob(Response->GetContentAsString());
            OnComplete(Result);
        });

    HttpRequest->ProcessRequest();
}

FPromptMotionRuntimeResponse FPromptMotionApiClient::ParseResponse(const FString& JsonBody)
{
    FPromptMotionRuntimeResponse Result;

    TSharedPtr<FJsonObject> Root;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonBody);
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
    {
        Result.ErrorMessage = FString::Printf(TEXT("JSON parse failed: %s"), *JsonBody.Left(200));
        return Result;
    }

    Root->TryGetStringField(TEXT("reply"), Result.Reply);

    const TSharedPtr<FJsonObject>* BehaviorObj;
    if (Root->TryGetObjectField(TEXT("behavior"), BehaviorObj) && BehaviorObj)
        ParseBehaviorObject(*BehaviorObj, Result.Behavior);

    const TSharedPtr<FJsonObject>* MetadataObj;
    if (Root->TryGetObjectField(TEXT("metadata"), MetadataObj) && MetadataObj)
        ParseMetadataObject(*MetadataObj, Result.Metadata);

    Result.bSuccess = true;
    return Result;
}

FPromptMotionTurnAsyncAccepted FPromptMotionApiClient::ParseTurnAccepted(const FString& JsonBody)
{
    FPromptMotionTurnAsyncAccepted Result;

    TSharedPtr<FJsonObject> Root;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonBody);
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
    {
        Result.ErrorMessage = FString::Printf(TEXT("JSON parse failed: %s"), *JsonBody.Left(200));
        return Result;
    }

    Root->TryGetStringField(TEXT("turnJobId"), Result.TurnJobId);
    Root->TryGetStringField(TEXT("status"), Result.Status);
    const TSharedPtr<FJsonObject>* ReactionObj;
    if (Root->TryGetObjectField(TEXT("reaction"), ReactionObj) && ReactionObj)
        ParseBehaviorObject(*ReactionObj, Result.Reaction);

    Result.bSuccess = !Result.TurnJobId.IsEmpty();
    if (!Result.bSuccess)
        Result.ErrorMessage = FString::Printf(TEXT("turnJobId missing: %s"), *JsonBody.Left(200));
    return Result;
}

FPromptMotionTurnAsyncJob FPromptMotionApiClient::ParseTurnJob(const FString& JsonBody)
{
    FPromptMotionTurnAsyncJob Result;

    TSharedPtr<FJsonObject> Root;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonBody);
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
    {
        Result.ErrorMessage = FString::Printf(TEXT("JSON parse failed: %s"), *JsonBody.Left(200));
        return Result;
    }

    Root->TryGetStringField(TEXT("turnJobId"), Result.TurnJobId);
    Root->TryGetStringField(TEXT("status"), Result.Status);
    Root->TryGetBoolField(TEXT("responseReady"), Result.bResponseReady);
    Root->TryGetBoolField(TEXT("ttsReady"), Result.bTtsReady);
    Root->TryGetStringField(TEXT("error"), Result.ErrorMessage);

    const TSharedPtr<FJsonObject>* ReactionObj;
    if (Root->TryGetObjectField(TEXT("reaction"), ReactionObj) && ReactionObj)
        ParseBehaviorObject(*ReactionObj, Result.Reaction);

    const TSharedPtr<FJsonObject>* ResponseObj;
    if (Root->TryGetObjectField(TEXT("response"), ResponseObj) && ResponseObj)
    {
        (*ResponseObj)->TryGetStringField(TEXT("reply"), Result.Response.Reply);
        const TSharedPtr<FJsonObject>* BehaviorObj;
        if ((*ResponseObj)->TryGetObjectField(TEXT("behavior"), BehaviorObj) && BehaviorObj)
            ParseBehaviorObject(*BehaviorObj, Result.Response.Behavior);
        const TSharedPtr<FJsonObject>* MetadataObj;
        if ((*ResponseObj)->TryGetObjectField(TEXT("metadata"), MetadataObj) && MetadataObj)
            ParseMetadataObject(*MetadataObj, Result.Response.Metadata);
        Result.Response.bSuccess = !Result.Response.Reply.IsEmpty();
    }

    const TSharedPtr<FJsonObject>* TimelineObj;
    if (Root->TryGetObjectField(TEXT("speechTimeline"), TimelineObj) && TimelineObj)
        ParseSpeechTimelineObject(*TimelineObj, Result.SpeechTimeline);

    Result.bSuccess = !Result.TurnJobId.IsEmpty();
    if (!Result.bSuccess && Result.ErrorMessage.IsEmpty())
        Result.ErrorMessage = FString::Printf(TEXT("turnJobId missing: %s"), *JsonBody.Left(200));
    return Result;
}

void FPromptMotionApiClient::ParseBehaviorObject(const TSharedPtr<FJsonObject>& BehaviorObj, FPromptMotionBehavior& OutBehavior)
{
    if (!BehaviorObj.IsValid())
        return;

    BehaviorObj->TryGetStringField(TEXT("emotion"), OutBehavior.Emotion);
    BehaviorObj->TryGetStringField(TEXT("intent"), OutBehavior.Intent);
    BehaviorObj->TryGetStringField(TEXT("gaze"), OutBehavior.Gaze);
    BehaviorObj->TryGetStringField(TEXT("gestureKey"), OutBehavior.GestureKey);
    BehaviorObj->TryGetStringField(TEXT("headMotion"), OutBehavior.HeadMotion);
    BehaviorObj->TryGetStringField(TEXT("ttsStyle"), OutBehavior.TtsStyle);

    double Temp = 0.0;
    if (BehaviorObj->TryGetNumberField(TEXT("intensity"), Temp))
        OutBehavior.Intensity = static_cast<float>(Temp);
    if (BehaviorObj->TryGetNumberField(TEXT("confidence"), Temp))
        OutBehavior.Confidence = static_cast<float>(Temp);
}

void FPromptMotionApiClient::ParseMetadataObject(const TSharedPtr<FJsonObject>& MetadataObj, FPromptMotionRuntimeMetadata& OutMetadata)
{
    if (!MetadataObj.IsValid())
        return;

    MetadataObj->TryGetStringField(TEXT("requestId"), OutMetadata.RequestId);
    MetadataObj->TryGetStringField(TEXT("provider"), OutMetadata.Provider);
    MetadataObj->TryGetStringField(TEXT("model"), OutMetadata.Model);
    MetadataObj->TryGetStringField(TEXT("techProfile"), OutMetadata.TechProfile);
    MetadataObj->TryGetStringField(TEXT("inputMode"), OutMetadata.InputMode);
    MetadataObj->TryGetBoolField(TEXT("fallbackUsed"), OutMetadata.bFallbackUsed);

    int32 TempInt = 0;
    if (MetadataObj->TryGetNumberField(TEXT("providerLatencyMs"), TempInt))
        OutMetadata.ProviderLatencyMs = TempInt;
    if (MetadataObj->TryGetNumberField(TEXT("totalServerMs"), TempInt))
        OutMetadata.TotalServerMs = TempInt;
}

void FPromptMotionApiClient::ParseSpeechTimelineObject(const TSharedPtr<FJsonObject>& TimelineObj, FPromptMotionSpeechTimeline& OutTimeline)
{
    if (!TimelineObj.IsValid())
        return;

    TimelineObj->TryGetStringField(TEXT("utteranceId"), OutTimeline.UtteranceId);
    const TSharedPtr<FJsonObject>* AudioObj;
    if (TimelineObj->TryGetObjectField(TEXT("audio"), AudioObj) && AudioObj)
    {
        (*AudioObj)->TryGetStringField(TEXT("url"), OutTimeline.Audio.Url);
        (*AudioObj)->TryGetStringField(TEXT("format"), OutTimeline.Audio.Format);
        OutTimeline.AudioUrl = OutTimeline.Audio.Url;
        double Duration = 0.0;
        if ((*AudioObj)->TryGetNumberField(TEXT("durationSeconds"), Duration))
        {
            OutTimeline.Audio.DurationSeconds = static_cast<float>(Duration);
            OutTimeline.DurationSeconds = static_cast<float>(Duration);
        }
    }

    TimelineObj->TryGetStringField(TEXT("provider"), OutTimeline.Provider);
    TimelineObj->TryGetStringField(TEXT("model"), OutTimeline.Model);
    int32 LatencyMs = -1;
    if (TimelineObj->TryGetNumberField(TEXT("ttsLatencyMs"), LatencyMs))
        OutTimeline.TtsLatencyMs = LatencyMs;

    const auto ParseVisemes = [](const TArray<TSharedPtr<FJsonValue>>* VisemesArr, TArray<FPromptMotionVisemeEvent>& OutVisemes)
    {
        if (!VisemesArr)
            return;
        OutVisemes.Reserve(VisemesArr->Num());
        for (const TSharedPtr<FJsonValue>& Item : *VisemesArr)
        {
            const TSharedPtr<FJsonObject>* VisObj;
            if (!Item->TryGetObject(VisObj) || !VisObj)
                continue;
            FPromptMotionVisemeEvent Event;
            int32 VisId = 0;
            double TimeSeconds = 0.0;
            double Weight = 1.0;
            (*VisObj)->TryGetNumberField(TEXT("id"), VisId);
            (*VisObj)->TryGetNumberField(TEXT("time"), TimeSeconds);
            (*VisObj)->TryGetNumberField(TEXT("weight"), Weight);
            Event.VisemeId = VisId;
            Event.TimeSeconds = static_cast<float>(TimeSeconds);
            Event.OffsetMs = static_cast<float>(TimeSeconds * 1000.0);
            Event.Weight = static_cast<float>(Weight);
            OutVisemes.Add(Event);
        }
    };

    const TArray<TSharedPtr<FJsonValue>>* VisemesArr;
    if (TimelineObj->TryGetArrayField(TEXT("visemes"), VisemesArr))
        ParseVisemes(VisemesArr, OutTimeline.Visemes);

    const TArray<TSharedPtr<FJsonValue>>* SegmentsArr;
    if (TimelineObj->TryGetArrayField(TEXT("segments"), SegmentsArr))
    {
        OutTimeline.Segments.Reserve(SegmentsArr->Num());
        for (const TSharedPtr<FJsonValue>& Item : *SegmentsArr)
        {
            const TSharedPtr<FJsonObject>* SegmentObj;
            if (!Item->TryGetObject(SegmentObj) || !SegmentObj)
                continue;

            FPromptMotionSpeechSegment Segment;
            (*SegmentObj)->TryGetStringField(TEXT("segmentId"), Segment.SegmentId);
            (*SegmentObj)->TryGetNumberField(TEXT("index"), Segment.Index);
            (*SegmentObj)->TryGetStringField(TEXT("text"), Segment.Text);
            double Start = 0.0;
            double Duration = 0.0;
            if ((*SegmentObj)->TryGetNumberField(TEXT("startTime"), Start))
                Segment.StartTime = static_cast<float>(Start);
            if ((*SegmentObj)->TryGetNumberField(TEXT("durationSeconds"), Duration))
                Segment.DurationSeconds = static_cast<float>(Duration);
            int32 SegmentLatency = -1;
            if ((*SegmentObj)->TryGetNumberField(TEXT("ttsLatencyMs"), SegmentLatency))
                Segment.TtsLatencyMs = SegmentLatency;

            const TSharedPtr<FJsonObject>* SegmentAudioObj;
            if ((*SegmentObj)->TryGetObjectField(TEXT("audio"), SegmentAudioObj) && SegmentAudioObj)
            {
                (*SegmentAudioObj)->TryGetStringField(TEXT("url"), Segment.Audio.Url);
                (*SegmentAudioObj)->TryGetStringField(TEXT("format"), Segment.Audio.Format);
                if ((*SegmentAudioObj)->TryGetNumberField(TEXT("durationSeconds"), Duration))
                    Segment.Audio.DurationSeconds = static_cast<float>(Duration);
            }

            const TArray<TSharedPtr<FJsonValue>>* SegmentVisemesArr;
            if ((*SegmentObj)->TryGetArrayField(TEXT("visemes"), SegmentVisemesArr))
                ParseVisemes(SegmentVisemesArr, Segment.Visemes);
            OutTimeline.Segments.Add(MoveTemp(Segment));
        }
    }
}
