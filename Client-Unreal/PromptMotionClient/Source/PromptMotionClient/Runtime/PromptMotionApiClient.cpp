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
    {
        (*BehaviorObj)->TryGetStringField(TEXT("emotion"),    Result.Behavior.Emotion);
        (*BehaviorObj)->TryGetStringField(TEXT("intent"),     Result.Behavior.Intent);
        (*BehaviorObj)->TryGetStringField(TEXT("gaze"),       Result.Behavior.Gaze);
        (*BehaviorObj)->TryGetStringField(TEXT("gestureKey"), Result.Behavior.GestureKey);
        (*BehaviorObj)->TryGetStringField(TEXT("headMotion"), Result.Behavior.HeadMotion);
        (*BehaviorObj)->TryGetStringField(TEXT("ttsStyle"),   Result.Behavior.TtsStyle);

        double Temp = 0.0;
        if ((*BehaviorObj)->TryGetNumberField(TEXT("intensity"), Temp))
            Result.Behavior.Intensity = static_cast<float>(Temp);
        if ((*BehaviorObj)->TryGetNumberField(TEXT("confidence"), Temp))
            Result.Behavior.Confidence = static_cast<float>(Temp);
    }

    Result.bSuccess = true;
    return Result;
}
