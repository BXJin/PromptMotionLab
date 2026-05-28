#include "PromptMotionRealtimeClient.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "PromptMotionLog.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Modules/ModuleManager.h"
#include "WebSocketsModule.h"

FPromptMotionRealtimeClient::FPromptMotionRealtimeClient(const FString& InWebSocketUrl)
    : WebSocketUrl(InWebSocketUrl)
{
}

FPromptMotionRealtimeClient::~FPromptMotionRealtimeClient()
{
    Close();
}

void FPromptMotionRealtimeClient::Connect()
{
    if (Socket.IsValid() && Socket->IsConnected())
    {
        return;
    }

    if (!FModuleManager::Get().IsModuleLoaded(TEXT("WebSockets")))
    {
        FModuleManager::LoadModuleChecked<FWebSocketsModule>(TEXT("WebSockets"));
    }

    Socket = FWebSocketsModule::Get().CreateWebSocket(WebSocketUrl);
    Socket->OnConnected().AddLambda([this]()
    {
        UE_LOG(LogPromptMotion, Log, TEXT("[PromptMotion] WebSocket connected: %s"), *WebSocketUrl);
        if (OnConnected)
        {
            OnConnected();
        }
    });
    Socket->OnConnectionError().AddLambda([this](const FString& Error)
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[PromptMotion] WebSocket connection error: %s"), *Error);
        if (OnError)
        {
            OnError(TEXT(""), Error);
        }
    });
    Socket->OnClosed().AddLambda([this](int32 StatusCode, const FString& Reason, bool bWasClean)
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[PromptMotion] WebSocket closed code=%d clean=%s reason=%s"),
            StatusCode, bWasClean ? TEXT("true") : TEXT("false"), *Reason);
        if (OnClosed)
        {
            OnClosed(Reason);
        }
    });
    Socket->OnMessage().AddRaw(this, &FPromptMotionRealtimeClient::HandleMessage);
    Socket->Connect();
}

void FPromptMotionRealtimeClient::Close()
{
    if (Socket.IsValid())
    {
        Socket->Close();
        Socket.Reset();
    }
}

bool FPromptMotionRealtimeClient::IsConnected() const
{
    return Socket.IsValid() && Socket->IsConnected();
}

void FPromptMotionRealtimeClient::SendRuntimeRequest(
    const FString& RequestId,
    const FString& SessionId,
    const FString& CharacterId,
    const FString& Message,
    const FPromptMotionSceneContext& SceneContext)
{
    if (!IsConnected())
    {
        if (OnError)
        {
            OnError(RequestId, TEXT("WebSocket is not connected"));
        }
        return;
    }

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

    TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetStringField(TEXT("type"), TEXT("runtime_request"));
    Root->SetStringField(TEXT("requestId"), RequestId);
    Root->SetStringField(TEXT("sessionId"), SessionId);
    Root->SetStringField(TEXT("characterId"), CharacterId);
    Root->SetStringField(TEXT("message"), Message);
    Root->SetObjectField(TEXT("sceneContext"), SceneJson);

    FString Payload;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Payload);
    FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);
    Socket->Send(Payload);
}

void FPromptMotionRealtimeClient::HandleMessage(const FString& Message)
{
    TSharedPtr<FJsonObject> Root;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
    {
        if (OnError)
        {
            OnError(TEXT(""), FString::Printf(TEXT("Invalid WebSocket JSON: %s"), *Message.Left(200)));
        }
        return;
    }

    FString Type;
    Root->TryGetStringField(TEXT("type"), Type);

    FString RequestId;
    Root->TryGetStringField(TEXT("requestId"), RequestId);

    if (Type == TEXT("reaction"))
    {
        HandleReaction(RequestId, Root);
    }
    else if (Type == TEXT("final"))
    {
        HandleFinal(RequestId, Root);
    }
    else if (Type == TEXT("error"))
    {
        HandleError(RequestId, Root);
    }
}

void FPromptMotionRealtimeClient::HandleReaction(const FString& RequestId, const TSharedPtr<FJsonObject>& Root)
{
    const TSharedPtr<FJsonObject>* BehaviorObj;
    if (!Root->TryGetObjectField(TEXT("behavior"), BehaviorObj) || !BehaviorObj)
    {
        if (OnError)
        {
            OnError(RequestId, TEXT("Reaction missing behavior"));
        }
        return;
    }

    if (OnReaction)
    {
        OnReaction(RequestId, ParseBehavior(*BehaviorObj));
    }
}

void FPromptMotionRealtimeClient::HandleFinal(const FString& RequestId, const TSharedPtr<FJsonObject>& Root)
{
    const TSharedPtr<FJsonObject>* ResponseObj;
    if (!Root->TryGetObjectField(TEXT("response"), ResponseObj) || !ResponseObj)
    {
        if (OnError)
        {
            OnError(RequestId, TEXT("Final missing response"));
        }
        return;
    }

    if (OnFinal)
    {
        OnFinal(RequestId, ParseRuntimeResponse(*ResponseObj));
    }
}

void FPromptMotionRealtimeClient::HandleError(const FString& RequestId, const TSharedPtr<FJsonObject>& Root)
{
    FString Error;
    Root->TryGetStringField(TEXT("error"), Error);
    if (OnError)
    {
        OnError(RequestId, Error);
    }
}

FPromptMotionBehavior FPromptMotionRealtimeClient::ParseBehavior(const TSharedPtr<FJsonObject>& BehaviorObj)
{
    FPromptMotionBehavior Behavior;
    if (!BehaviorObj.IsValid())
    {
        return Behavior;
    }

    BehaviorObj->TryGetStringField(TEXT("emotion"), Behavior.Emotion);
    BehaviorObj->TryGetStringField(TEXT("intent"), Behavior.Intent);
    BehaviorObj->TryGetStringField(TEXT("gaze"), Behavior.Gaze);
    BehaviorObj->TryGetStringField(TEXT("gestureKey"), Behavior.GestureKey);
    BehaviorObj->TryGetStringField(TEXT("headMotion"), Behavior.HeadMotion);
    BehaviorObj->TryGetStringField(TEXT("ttsStyle"), Behavior.TtsStyle);

    double Temp = 0.0;
    if (BehaviorObj->TryGetNumberField(TEXT("intensity"), Temp))
        Behavior.Intensity = static_cast<float>(Temp);
    if (BehaviorObj->TryGetNumberField(TEXT("confidence"), Temp))
        Behavior.Confidence = static_cast<float>(Temp);

    return Behavior;
}

FPromptMotionRuntimeMetadata FPromptMotionRealtimeClient::ParseMetadata(const TSharedPtr<FJsonObject>& MetadataObj)
{
    FPromptMotionRuntimeMetadata Metadata;
    if (!MetadataObj.IsValid())
    {
        return Metadata;
    }

    MetadataObj->TryGetStringField(TEXT("requestId"), Metadata.RequestId);
    MetadataObj->TryGetStringField(TEXT("provider"), Metadata.Provider);
    MetadataObj->TryGetStringField(TEXT("model"), Metadata.Model);
    MetadataObj->TryGetStringField(TEXT("techProfile"), Metadata.TechProfile);
    MetadataObj->TryGetStringField(TEXT("inputMode"), Metadata.InputMode);
    MetadataObj->TryGetBoolField(TEXT("fallbackUsed"), Metadata.bFallbackUsed);

    int32 TempInt = 0;
    if (MetadataObj->TryGetNumberField(TEXT("providerLatencyMs"), TempInt))
        Metadata.ProviderLatencyMs = TempInt;
    if (MetadataObj->TryGetNumberField(TEXT("totalServerMs"), TempInt))
        Metadata.TotalServerMs = TempInt;

    return Metadata;
}

FPromptMotionRuntimeResponse FPromptMotionRealtimeClient::ParseRuntimeResponse(const TSharedPtr<FJsonObject>& ResponseObj)
{
    FPromptMotionRuntimeResponse Response;
    if (!ResponseObj.IsValid())
    {
        Response.ErrorMessage = TEXT("Invalid final response");
        return Response;
    }

    ResponseObj->TryGetStringField(TEXT("reply"), Response.Reply);

    const TSharedPtr<FJsonObject>* BehaviorObj;
    if (ResponseObj->TryGetObjectField(TEXT("behavior"), BehaviorObj) && BehaviorObj)
    {
        Response.Behavior = ParseBehavior(*BehaviorObj);
    }

    const TSharedPtr<FJsonObject>* MetadataObj;
    if (ResponseObj->TryGetObjectField(TEXT("metadata"), MetadataObj) && MetadataObj)
    {
        Response.Metadata = ParseMetadata(*MetadataObj);
    }

    Response.bSuccess = true;
    return Response;
}
