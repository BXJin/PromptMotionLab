#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "HAL/ThreadSafeCounter.h"
#include "PromptMotionApiClient.h"
#include "PromptMotionRealtimeClient.h"
#include "PromptMotionLatencyLogger.h"
#include "PromptMotionRuntimeEndpointConfig.h"
#include "PromptMotionSpeechPlaybackController.h"
#include "PromptMotionSttClient.h"
#include "PromptMotionTypes.h"
#include "PromptMotionVoiceInputController.h"
#include "FaceIdleLayer.h"
#include "FaceLipSyncLayer.h"
#include "FaceSpeechMicroLayer.h"
#include "PromptMotionRuntimeComponent.generated.h"

class USkeletalMeshComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnRuntimeResponseReceived, const FPromptMotionRuntimeResponse&, Response);

UENUM(BlueprintType)
enum class EPromptMotionConversationMode : uint8
{
    Casual UMETA(DisplayName="Casual"),
    EnglishTutor UMETA(DisplayName="English Tutor"),
    Guide UMETA(DisplayName="Guide"),
};

UENUM(BlueprintType)
enum class EPromptMotionVoiceStatus : uint8
{
    Idle UMETA(DisplayName="Idle"),
    Listening UMETA(DisplayName="Listening"),
    UserSpeaking UMETA(DisplayName="User Speaking"),
    Transcribing UMETA(DisplayName="Transcribing"),
    Thinking UMETA(DisplayName="Thinking"),
    CharacterSpeaking UMETA(DisplayName="Character Speaking"),
    Cooldown UMETA(DisplayName="Cooldown"),
    Error UMETA(DisplayName="Error"),
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnPromptMotionVoiceStatusChanged, EPromptMotionVoiceStatus, Status);

/**
 * AI 캐릭터 런타임 컴포넌트.
 *
 * 사용법:
 *   1. Actor에 컴포넌트 추가.
 *   2. ServerUrl, SessionId, CharacterId, TargetMesh 설정.
 *   3. Blueprint에서 SendRuntimeMessage(Message) 호출.
 *   4. OnRuntimeResponseReceived 이벤트에서 Reply, Behavior 처리.
 *   5. 응답 수신 즉시 TargetMesh에 FacePreset 자동 적용.
 */
UCLASS(ClassGroup=(PromptMotion), meta=(BlueprintSpawnableComponent))
class PROMPTMOTIONCLIENT_API UPromptMotionRuntimeComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UPromptMotionRuntimeComponent();

    // ------------------------------------------------------------------
    // 설정
    // ------------------------------------------------------------------

    /** Python 서버 주소. 기본값: http://localhost:8010 */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Config")
    FString ServerUrl = TEXT("http://localhost:8010");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Config")
    bool bLoadEndpointConfigOnBeginPlay = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Config")
    FString EndpointConfigProfileOverride;

    /** 세션 식별자 */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Config")
    FString SessionId = TEXT("demo_session");

    /** 캐릭터 식별자 */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Config")
    FString CharacterId = TEXT("default_girl");

    /** Face/lip-sync CSV config id. Personality presets can share one character rig config. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Config")
    FString FaceConfigId = TEXT("default_girl");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Config")
    EPromptMotionConversationMode ConversationMode = EPromptMotionConversationMode::Casual;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Realtime")
    bool bUseRealtimeWebSocket = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Realtime")
    bool bUseAsyncTurnHttp = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Realtime", meta=(ClampMin="0.05", ClampMax="2.0"))
    float AsyncTurnPollIntervalSeconds = 0.2f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Realtime")
    FString WebSocketUrl = TEXT("ws://localhost:8010/ws/runtime");

    /**
     * 표정 morph를 적용할 SkeletalMeshComponent.
     * 비워두면 Owner Actor에서 자동 탐색 (FindComponentByClass).
     */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Config")
    TObjectPtr<USkeletalMeshComponent> TargetMesh;

    // ------------------------------------------------------------------
    // Blueprint 이벤트
    // ------------------------------------------------------------------

    /** 서버 응답 수신 시 발생. Blueprint에서 바인딩해 Reply/Behavior 처리. */
    UPROPERTY(BlueprintAssignable, Category="PromptMotion|Events")
    FOnRuntimeResponseReceived OnRuntimeResponseReceived;

    UPROPERTY(BlueprintAssignable, Category="PromptMotion|Events")
    FOnPromptMotionVoiceStatusChanged OnVoiceStatusChanged;

    // ------------------------------------------------------------------
    // 마지막 응답 캐시 (Blueprint 직접 참조용)
    // ------------------------------------------------------------------

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion|State")
    FString LastReply;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion|State")
    FPromptMotionBehavior LastBehavior;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion|State")
    EPromptMotionVoiceStatus VoiceStatus = EPromptMotionVoiceStatus::Idle;

    // ------------------------------------------------------------------
    // Blueprint 호출 함수
    // ------------------------------------------------------------------

    /** 인게임 UI용 캐릭터 프리셋 목록. 서버 character_profile과 일치해야 함. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Config")
    TArray<FString> CharacterPresets;

    /**
     * 런타임에 캐릭터 변경. 다른 캐릭터이면 SessionId도 자동 리셋해
     * 이전 대화 히스토리가 섞이지 않도록 함.
     */
    UFUNCTION(BlueprintCallable, Category="PromptMotion")
    void SetCharacterId(const FString& NewCharacterId);

    /** 메시지만 보낼 때. SceneContext는 빈 값으로 전송. */
    UFUNCTION(BlueprintCallable, Category="PromptMotion")
    void SendRuntimeMessage(const FString& Message);

    /** SceneContext 포함해서 보낼 때. */
    UFUNCTION(BlueprintCallable, Category="PromptMotion")
    void SendRuntimeMessageWithContext(const FString& Message, const FPromptMotionSceneContext& SceneContext);

    UFUNCTION(BlueprintCallable, Category="PromptMotion")
    void SetConversationMode(EPromptMotionConversationMode NewMode);

    UFUNCTION(BlueprintCallable, Category="PromptMotion|Voice")
    bool StartPushToTalk();

    UFUNCTION(BlueprintCallable, Category="PromptMotion|Voice")
    bool StopPushToTalkAndSend();

    UFUNCTION(BlueprintCallable, Category="PromptMotion|Voice")
    void SetVoiceVadEnabled(bool bEnabled);

    UFUNCTION(BlueprintCallable, Category="PromptMotion|Voice")
    bool RequestMicrophonePermission();

    /**
     * emotion + intensity를 TargetMesh morph target에 직접 적용.
     * BlendDuration 동안 현재 표정에서 부드럽게 전환됨.
     * 응답 수신 시 자동 호출되며, Blueprint에서도 수동 호출 가능.
     */
    UFUNCTION(BlueprintCallable, Category="PromptMotion")
    void ApplyFacePreset(const FString& Emotion, float Intensity);

    UFUNCTION(BlueprintCallable, Category="PromptMotion|Debug")
    void ReloadFaceConfig();

    UFUNCTION(BlueprintCallable, Category="PromptMotion|Debug")
    void ApplyDebugMorph(FName MorphName, float Weight);

    UFUNCTION(BlueprintCallable, Category="PromptMotion|Debug")
    void ApplyDebugViseme(int32 VisemeId, float Weight = 1.0f);

    UFUNCTION(BlueprintCallable, Category="PromptMotion|Debug")
    bool SaveDebugLipSyncVisemeWeight(int32 VisemeId, FName MorphName, float Weight);

    UFUNCTION(BlueprintCallable, Category="PromptMotion|Debug")
    bool SaveDebugFacePresetWeight(const FString& Preset, FName MorphName, float Weight);

    /** 현재 캐시에서 preset + morph의 저장된 weight 반환. Debug UI 슬라이더 초기화용. */
    UFUNCTION(BlueprintCallable, Category="PromptMotion|Debug")
    float QueryDebugFaceWeight(const FString& Preset, FName MorphName) const;

    /** 현재 매핑에서 visemeId + morph의 저장된 weight 반환. Debug UI 슬라이더 초기화용. */
    UFUNCTION(BlueprintCallable, Category="PromptMotion|Debug")
    float QueryDebugVisemeWeight(int32 VisemeId, FName MorphName) const;

    // ------------------------------------------------------------------
    // 블렌딩 설정
    // ------------------------------------------------------------------

    /**
     * 표정 전환 시간(초). 0으로 설정하면 즉시 전환.
     * 기본 0.3초 — 대화 응답 표정 전환에 자연스러운 속도.
     */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Config", meta=(ClampMin="0.0", ClampMax="2.0"))
    float BlendDuration = 0.3f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Metrics")
    bool bEnableLatencyCsv = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Metrics")
    FString LatencyTechProfile = TEXT("text_llm_behavior_json_v1");

    // ------------------------------------------------------------------
    // TTS 설정
    // ------------------------------------------------------------------

    /** TTS 합성 활성화 여부. false면 TTS 요청 없이 텍스트만 수신. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|TTS")
    bool bEnableTts = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|TTS", meta=(ClampMin="0.05", ClampMax="0.5"))
    float LipSyncPostLastVisemeReleaseSeconds = 0.18f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice")
    bool bEnableVoiceInput = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice")
    bool bEnableStreamingStt = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice")
    FString StreamingSttWebSocketUrl = TEXT("ws://127.0.0.1:8010/ws/stt");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice")
    FString SttLanguage = TEXT("ko");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice", meta=(ClampMin="8000", ClampMax="48000"))
    int32 VoiceSampleRate = 16000;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice", meta=(ClampMin="0.001", ClampMax="1.0"))
    float VadStartRmsThreshold = 0.035f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice", meta=(ClampMin="0.001", ClampMax="1.0"))
    float VadEndRmsThreshold = 0.018f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice", meta=(ClampMin="0.05", ClampMax="5.0"))
    float VadMinSpeechSeconds = 0.25f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice", meta=(ClampMin="0.1", ClampMax="3.0"))
    float VadEndSilenceSeconds = 0.55f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice", meta=(ClampMin="0.0", ClampMax="2.0"))
    float VoiceTtsCooldownSeconds = 0.4f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice", meta=(ClampMin="0.1", ClampMax="5.0"))
    float VoiceErrorHoldSeconds = 1.25f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice", meta=(ClampMin="0.005", ClampMax="0.2"))
    float VoicePollIntervalSeconds = 0.02f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice")
    bool bEnableVoiceBargeIn = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice|Debug")
    bool bUseDebugSttWavForPushToTalk = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Voice|Debug")
    FString DebugSttWavPath = TEXT("../../Build/reports/stt_smoke/sample_hello_weather.wav");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Debug")
    bool bAllowDebugMorphControl = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Face")
    bool bEnableIdleBlink = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Face")
    bool bEnableSpeechMicroExpression = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Face")
    bool bEnableIdleExpression = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Face", meta=(ClampMin="0.0", ClampMax="10.0"))
    float ResponseEmotionHoldSeconds = 2.5f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Face", meta=(ClampMin="0.5", ClampMax="12.0"))
    float ResponseEmotionDecaySeconds = 4.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Face", meta=(ClampMin="0.0", ClampMax="0.5"))
    float IdleExpressionIntensity = 0.18f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Face", meta=(ClampMin="0.0", ClampMax="2.0"))
    float ExpressionIntensityMin = 0.65f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Face", meta=(ClampMin="0.0", ClampMax="2.0"))
    float ExpressionIntensityMax = 1.15f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Face", meta=(ClampMin="0.0", ClampMax="2.0"))
    float ExpressionIntensityMultiplier = 1.0f;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
    struct FPendingRealtimeRequest
    {
        int32 RequestId = 0;
        FString Message;
        FPromptMotionSceneContext SceneContext;
    };

    TUniquePtr<FPromptMotionApiClient> ApiClient;
    TUniquePtr<FPromptMotionRealtimeClient> RealtimeClient;
    TSharedPtr<FPromptMotionVoiceInputController> VoiceInputController;
    TSharedPtr<FPromptMotionSpeechPlaybackController> SpeechPlaybackController;
    TUniquePtr<FPromptMotionSttClient> DebugSttClient;

    FString CachedBaseUrl;
    FString CachedDebugSttBaseUrl;
    FString CachedWebSocketUrl;
    FString ActiveRealtimeRequestId;
    TMap<FString, double> RealtimeRequestStartTimes;
    TMap<FString, double> RealtimeFirstVisibleMs;
    TMap<FString, FString> RealtimeMessages;
    TArray<FPendingRealtimeRequest> PendingRealtimeRequests;
    TMap<FString, int32> TurnJobRequestIds;
    TMap<FString, double> TurnJobRequestStartTimes;
    TMap<FString, double> TurnJobFirstVisibleMs;
    TMap<FString, FString> TurnJobMessages;
    TSet<FString> TurnJobResponseApplied;
    TSet<FString> TurnJobTtsStarted;

    double LastTtsStopWorldSeconds = -1000.0;
    double VoiceErrorStartedWorldSeconds = -1000.0;
    bool bPendingVoiceTrace = false;
    bool bMicrophonePermissionGranted = true;
    bool bDebugSttInFlight = false;
    FPromptMotionVoiceLatencyTrace PendingVoiceTrace;
    FPromptMotionVoiceLatencyTrace ActiveVoiceTrace;
    mutable int32 LastSttLatencyMs = -1;

    // ------------------------------------------------------------------
    // TTS / LipSync 내부 상태
    // ------------------------------------------------------------------

    FFaceLipSyncLayer LipSyncLayer;
    FFaceIdleLayer IdleFaceLayer;
    FFaceSpeechMicroLayer SpeechMicroLayer;

    /** TTS 오디오 재생 컴포넌트. BeginPlay 이후 처음 사용 시 생성. */
    /** 진행 중인 viseme 타이머 핸들. 새 TTS 시작 시 이전 타이머를 모두 클리어. */
    /** 현재 TTS 요청과 연결된 LLM requestId. 스테일 응답 무시에 사용. */
    FString ActiveTtsRequestId;

    FPromptMotionSpeechTimeline ActiveSpeechTimeline;
    bool bLipSyncActive = false;
    double LipSyncStartWorldSeconds = 0.0;
    int32 LastAppliedVisemeIndex = INDEX_NONE;
    int32 LastAppliedVisemeId = INDEX_NONE;

    /** 진행 중인 요청 ID. SendRuntimeMessage마다 증가. 응답 수신 시 일치하지 않으면 무시. */
    FThreadSafeCounter RequestIdCounter;

    // ------------------------------------------------------------------
    // 블렌딩 내부 상태
    // ------------------------------------------------------------------

    /** 현재 메시에 실제로 적용된 morph weight. 블렌드 완료 시점 또는 즉시 적용 시 갱신. */
    TMap<FName, float> CurrentWeights;

    /** 블렌드 시작 시점의 morph weight 스냅샷. 선형 보간의 A값으로 사용. */
    TMap<FName, float> InitialWeights;

    /** 블렌딩 목표 morph weight 값. ApplyFacePreset 호출 시 갱신. */
    TMap<FName, float> TargetWeights;
    TMap<FName, FPromptMotionFaceMorphSetting> TargetFaceSettings;

    /** 현재 블렌드에서 경과한 시간(초). */
    float BlendElapsed = 0.0f;
    float ActiveBlendDuration = 0.0f;
    float NextBlendDurationOverride = -1.0f;
    bool bFaceBlendActive = false;
    FString LastResponseEmotion;
    double LastResponseEmotionAppliedWorldSeconds = -1000.0;

    float RemapExpressionIntensity(float Intensity) const;
    float GetEffectiveFaceWeight(FName MorphName, const FPromptMotionFaceMorphSetting& Setting) const;
    float GetFaceInterpSpeed(FName MorphName, float Current, float Target) const;
    void ApplySpeechMicroOffsets(USkeletalMeshComponent* Mesh);
    void ApplyIdleExpressionIfNeeded(float DeltaTime);
    FString ResolveIdleEmotion() const;
    float ResolveIdleIntensity() const;

    void EnsureApiClient();
    void EnsureRealtimeClient();
    void ConfigureVoiceInputController();
    void ConfigureSpeechPlaybackController();
    bool HasMicrophonePermission() const;
    bool ShouldIgnoreVoiceForTtsCooldown() const;
    bool IsVoiceSubmissionBlocked() const;
    bool IsVoiceInputActive() const;
    void SetVoiceStatus(EPromptMotionVoiceStatus NewStatus);
    bool SubmitDebugSttWav(double NowSeconds);
    FString ResolveDebugSttWavPath() const;
    void EnsureDebugSttClient();
    void AttachVoiceTraceToRequest(int32 RequestId, double LlmRequestSentSeconds);
    void AppendVoiceLatencyCsv(const FPromptMotionRuntimeResponse* Response, const FString& Notes) const;
    void ApplyEndpointConfig();

    UFUNCTION()
    void HandleAndroidMicrophonePermissionResult(const TArray<FString>& Permissions, const TArray<bool>& GrantResults);
    void SendRuntimeMessageWithHttp(const FString& Message, const FPromptMotionSceneContext& SceneContext, int32 ThisRequestId);
    void SendRuntimeMessageWithTurnAsync(const FString& Message, const FPromptMotionSceneContext& SceneContext, int32 ThisRequestId);
    void PollTurnAsyncJob(const FString& TurnJobId);
    void CleanupTurnAsyncJob(const FString& TurnJobId);
    void SendRuntimeMessageWithWebSocket(const FString& Message, const FPromptMotionSceneContext& SceneContext, int32 ThisRequestId);
    void FlushPendingRealtimeRequests();
    void FallbackPendingRealtimeRequests(const FString& Reason);
    bool IsStaleRealtimeRequest(const FString& RequestId) const;
    int32 ParseUnrealRequestId(const FString& RequestId) const;

    /**
     * LLM 응답 수신 후 TTS 합성 → WAV 다운로드 → 재생 + viseme 스케줄링.
     * LlmRequestId: 스테일 체크용. 해당 요청이 취소됐으면 조용히 종료.
     */
    void StartTtsForResponse(
        const FString& LlmRequestId,
        const FString& ReplyText,
        const FString& TtsStyle);

    void StartTtsTimelineForResponse(
        const FString& LlmRequestId,
        const FPromptMotionSpeechTimeline& Timeline);

    /** 진행 중인 TTS 타이머 전체 클리어 + LipSync 리셋. */
    void CancelActiveTts();

    /** WAV 바이너리 → USoundWaveProcedural 생성 후 재생. */
    /** viseme 이벤트 배열로 FTimerHandle 스케줄 등록. */
    void StartLipSyncTimeline(const FPromptMotionSpeechTimeline& Timeline);
    void UpdateLipSyncFromAudioTime(float AudioSeconds);
    void StopLipSyncTimeline();

    /** TargetMesh가 설정되어 있으면 반환, 없으면 Owner에서 자동 탐색. */
    USkeletalMeshComponent* ResolveTargetMesh() const;

    void AppendLatencyCsv(
        int32 RequestId,
        const FString& Message,
        const FPromptMotionRuntimeResponse& Response,
        double RequestStartTime,
        double ResponseReceivedTime,
        double FirstVisibleReactionMs) const;
};
