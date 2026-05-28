#pragma once

#include "CoreMinimal.h"
#include "PromptMotionTypes.generated.h"

/**
 * 서버 POST /api/runtime/respond 요청 시 함께 보내는 씬 컨텍스트.
 * Python SceneContext 모델과 1:1 대응.
 */
USTRUCT(BlueprintType)
struct FPromptMotionSceneContext
{
    GENERATED_BODY()

    /** 현재 위치 ID (전시 구역, 섹션 등) */
    UPROPERTY(BlueprintReadWrite, Category="PromptMotion")
    FString LocationId;

    /** 관람객이 주목하는 오브젝트 ID */
    UPROPERTY(BlueprintReadWrite, Category="PromptMotion")
    FString FocusedObjectId;

    /** 주변 오브젝트 ID 목록 */
    UPROPERTY(BlueprintReadWrite, Category="PromptMotion")
    TArray<FString> NearbyObjectIds;

    /** 현재 인터랙션 모드 (kiosk, guided, freeform 등) */
    UPROPERTY(BlueprintReadWrite, Category="PromptMotion")
    FString InteractionMode;
};

USTRUCT(BlueprintType)
struct FPromptMotionRuntimeMetadata
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString RequestId;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString Provider;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString Model;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString TechProfile;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString InputMode = TEXT("text");

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    bool bFallbackUsed = false;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    int32 ProviderLatencyMs = -1;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    int32 TotalServerMs = -1;
};

/**
 * 서버 응답 중 behavior 필드.
 * Python BehaviorJson 모델과 1:1 대응.
 */
USTRUCT(BlueprintType)
struct FPromptMotionBehavior
{
    GENERATED_BODY()

    /** 감정 레이블 (neutral, friendly, happy, thinking, concerned 등) */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString Emotion = TEXT("neutral");

    /** 감정 강도 0.0 ~ 1.0 */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    float Intensity = 0.6f;

    /** 응답 확신도 0.0 ~ 1.0 */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    float Confidence = 0.8f;

    /** 대화 의도 (greet, explain, answer, clarify, refuse, fallback) */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString Intent = TEXT("answer");

    /** 시선 타겟 (user, focused_object, down_left, side, none) */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString Gaze = TEXT("user");

    /** 제스처 키 (none, small_ack, explain_small, point_soft, hesitate, greet_small) */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString GestureKey = TEXT("small_ack");

    /** 헤드 모션 (none, small_nod, small_tilt, thinking_tilt) */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString HeadMotion = TEXT("small_nod");

    /** TTS 스타일 (neutral, warm, careful, energetic) */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString TtsStyle = TEXT("warm");
};

USTRUCT(BlueprintType)
struct FPromptMotionSpeechAudio
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString Url;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    float DurationSeconds = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString Format = TEXT("wav");
};

USTRUCT(BlueprintType)
struct FPromptMotionVisemeEvent
{
    GENERATED_BODY()

    /** Azure TTS viseme ID (0~21) */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    int32 VisemeId = 0;

    /** 발화 시작으로부터의 오프셋 (ms) */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    float OffsetMs = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    float TimeSeconds = 0.f;

    /** 해당 viseme 지속 시간 (ms). Phase 2 Behavior Segment Sync 이전까지 항상 0. */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    float DurationMs = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    float Weight = 1.f;
};

USTRUCT(BlueprintType)
struct FPromptMotionSpeechSegment
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString SegmentId;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    int32 Index = 0;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString Text;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    float StartTime = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    float DurationSeconds = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FPromptMotionSpeechAudio Audio;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    TArray<FPromptMotionVisemeEvent> Visemes;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    int32 TtsLatencyMs = -1;
};

USTRUCT(BlueprintType)
struct FPromptMotionSpeechTimeline
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString UtteranceId;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FPromptMotionSpeechAudio Audio;

    /** GET /api/runtime/audio/{utteranceId}.wav 상대 경로 */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString AudioUrl;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    float DurationSeconds = 0.f;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    TArray<FPromptMotionVisemeEvent> Visemes;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    TArray<FPromptMotionSpeechSegment> Segments;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString Provider;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString Model;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    int32 TtsLatencyMs = -1;
};

/**
 * POST /api/runtime/respond 전체 응답.
 */
USTRUCT(BlueprintType)
struct FPromptMotionRuntimeResponse
{
    GENERATED_BODY()

    /** 요청 성공 여부 */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    bool bSuccess = false;

    /** 캐릭터가 말할 텍스트 */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString Reply;

    /** Behavior JSON — 표정/시선/제스처 제어에 사용 */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FPromptMotionBehavior Behavior;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FPromptMotionRuntimeMetadata Metadata;

    /** 실패 시 에러 메시지 */
    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString ErrorMessage;
};

USTRUCT(BlueprintType)
struct FPromptMotionTurnAsyncAccepted
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    bool bSuccess = false;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString TurnJobId;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString Status;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FPromptMotionBehavior Reaction;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString ErrorMessage;
};

USTRUCT(BlueprintType)
struct FPromptMotionTurnAsyncJob
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    bool bSuccess = false;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString TurnJobId;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString Status;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FPromptMotionBehavior Reaction;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    bool bResponseReady = false;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    bool bTtsReady = false;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FPromptMotionRuntimeResponse Response;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FPromptMotionSpeechTimeline SpeechTimeline;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion")
    FString ErrorMessage;
};
