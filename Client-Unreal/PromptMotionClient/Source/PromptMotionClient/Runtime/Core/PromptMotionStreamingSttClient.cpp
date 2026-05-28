#include "PromptMotionStreamingSttClient.h"

#include "Dom/JsonObject.h"
#include "HAL/PlatformTime.h"
#include "Modules/ModuleManager.h"
#include "PromptMotionLog.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "WebSocketsModule.h"

FPromptMotionStreamingSttClient::FPromptMotionStreamingSttClient(const FString& InWebSocketUrl)
    : WebSocketUrl(InWebSocketUrl)
{
}

FPromptMotionStreamingSttClient::~FPromptMotionStreamingSttClient()
{
    Close();
}

void FPromptMotionStreamingSttClient::Start(const FString& Language, int32 SampleRate)
{
    PendingLanguage = Language;
    PendingSampleRate = SampleRate;
    StreamStartedSeconds = FPlatformTime::Seconds();
    PendingAudioChunks.Reset();
    bStopRequested = false;
    if (!IsConnected())
    {
        Connect();
        return;
    }
    SendStartMessage();
}

void FPromptMotionStreamingSttClient::SendAudioChunk(const TArray<uint8>& PcmBytes)
{
    if (PcmBytes.IsEmpty())
        return;
    if (!IsConnected() || !bStreaming)
    {
        PendingAudioChunks.Add(PcmBytes);
        return;
    }
    Socket->Send(PcmBytes.GetData(), PcmBytes.Num(), true);
}

void FPromptMotionStreamingSttClient::Stop()
{
    if (!IsConnected())
        return;

    FlushPendingAudioChunks();

    TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetStringField(TEXT("type"), TEXT("stop"));
    FString Payload;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Payload);
    FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);
    Socket->Send(Payload);
    bStopRequested = true;
    bStreaming = false;
}

void FPromptMotionStreamingSttClient::Close()
{
    bStreaming = false;
    bStopRequested = false;
    PendingAudioChunks.Reset();
    if (Socket.IsValid())
    {
        Socket->Close();
        Socket.Reset();
    }
}

bool FPromptMotionStreamingSttClient::IsConnected() const
{
    return Socket.IsValid() && Socket->IsConnected();
}

void FPromptMotionStreamingSttClient::Connect()
{
    if (!FModuleManager::Get().IsModuleLoaded(TEXT("WebSockets")))
        FModuleManager::LoadModuleChecked<FWebSocketsModule>(TEXT("WebSockets"));

    Socket = FWebSocketsModule::Get().CreateWebSocket(WebSocketUrl);
    Socket->OnConnected().AddLambda([this]()
    {
        UE_LOG(LogPromptMotion, Log, TEXT("[STT] Streaming WebSocket connected: %s"), *WebSocketUrl);
        SendStartMessage();
    });
    Socket->OnConnectionError().AddLambda([this](const FString& Error)
    {
        bStreaming = false;
        UE_LOG(LogPromptMotion, Warning, TEXT("[STT] Streaming WebSocket connection error: %s url=%s"), *Error, *WebSocketUrl);
        if (OnError)
            OnError(Error);
    });
    Socket->OnClosed().AddLambda([this](int32 StatusCode, const FString& Reason, bool bWasClean)
    {
        const bool bExpectedAfterStop = bStopRequested;
        bStreaming = false;
        bStopRequested = false;
        if (bExpectedAfterStop)
        {
            UE_LOG(LogPromptMotion, Verbose, TEXT("[STT] Streaming WebSocket closed after stop code=%d clean=%s reason=%s"),
                StatusCode, bWasClean ? TEXT("true") : TEXT("false"), *Reason);
        }
        else
        {
            UE_LOG(LogPromptMotion, Warning, TEXT("[STT] Streaming WebSocket closed code=%d clean=%s reason=%s"),
                StatusCode, bWasClean ? TEXT("true") : TEXT("false"), *Reason);
        }
        if (OnClosed)
            OnClosed();
    });
    Socket->OnMessage().AddRaw(this, &FPromptMotionStreamingSttClient::HandleMessage);
    Socket->Connect();
}

void FPromptMotionStreamingSttClient::SendStartMessage()
{
    if (!IsConnected())
        return;

    TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetStringField(TEXT("type"), TEXT("start"));
    Root->SetStringField(TEXT("language"), PendingLanguage);
    Root->SetNumberField(TEXT("sampleRate"), PendingSampleRate);
    FString Payload;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Payload);
    FJsonSerializer::Serialize(Root.ToSharedRef(), Writer);
    Socket->Send(Payload);
}

void FPromptMotionStreamingSttClient::FlushPendingAudioChunks()
{
    if (!IsConnected() || !bStreaming)
        return;

    for (const TArray<uint8>& Chunk : PendingAudioChunks)
        Socket->Send(Chunk.GetData(), Chunk.Num(), true);
    PendingAudioChunks.Reset();
}

void FPromptMotionStreamingSttClient::HandleMessage(const FString& Message)
{
    TSharedPtr<FJsonObject> Root;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);
    if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
        return;

    FString Type;
    Root->TryGetStringField(TEXT("type"), Type);
    if (Type == TEXT("started"))
    {
        bStreaming = true;
        FlushPendingAudioChunks();
        if (OnStarted)
            OnStarted();
        return;
    }
    if (Type == TEXT("partial"))
    {
        FString Text;
        Root->TryGetStringField(TEXT("text"), Text);
        if (OnPartial && !Text.IsEmpty())
            OnPartial(Text);
        return;
    }
    if (Type == TEXT("final"))
    {
        FPromptMotionSttResult Result;
        Root->TryGetStringField(TEXT("text"), Result.Text);
        Root->TryGetStringField(TEXT("language"), Result.Language);
        Root->TryGetStringField(TEXT("provider"), Result.Provider);
        Root->TryGetStringField(TEXT("model"), Result.Model);
        int32 Latency = 0;
        if (Root->TryGetNumberField(TEXT("sttLatencyMs"), Latency))
            Result.SttLatencyMs = Latency;
        if (OnFinal && !Result.Text.IsEmpty())
            OnFinal(Result);
        return;
    }
    if (Type == TEXT("error"))
    {
        FString Error;
        Root->TryGetStringField(TEXT("error"), Error);
        if (OnError)
            OnError(Error);
    }
}
