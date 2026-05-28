#pragma once

#include "CoreMinimal.h"
#include "IWebSocket.h"
#include "PromptMotionSttClient.h"

class FPromptMotionStreamingSttClient
{
public:
    explicit FPromptMotionStreamingSttClient(const FString& InWebSocketUrl);
    ~FPromptMotionStreamingSttClient();

    void Start(const FString& Language, int32 SampleRate);
    void SendAudioChunk(const TArray<uint8>& PcmBytes);
    void Stop();
    void Close();

    bool IsConnected() const;
    bool IsStreaming() const { return bStreaming; }

    TFunction<void()> OnStarted;
    TFunction<void(const FString& Text)> OnPartial;
    TFunction<void(const FPromptMotionSttResult& Result)> OnFinal;
    TFunction<void(const FString& Error)> OnError;
    TFunction<void()> OnClosed;

private:
    FString WebSocketUrl;
    TSharedPtr<IWebSocket> Socket;
    FString PendingLanguage;
    int32 PendingSampleRate = 16000;
    bool bStreaming = false;
    bool bStopRequested = false;
    double StreamStartedSeconds = 0.0;
    TArray<TArray<uint8>> PendingAudioChunks;

    void Connect();
    void SendStartMessage();
    void FlushPendingAudioChunks();
    void HandleMessage(const FString& Message);
};
