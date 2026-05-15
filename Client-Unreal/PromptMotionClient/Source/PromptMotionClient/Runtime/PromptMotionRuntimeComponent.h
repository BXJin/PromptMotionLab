#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "HAL/ThreadSafeCounter.h"
#include "PromptMotionApiClient.h"
#include "PromptMotionTypes.h"
#include "PromptMotionRuntimeComponent.generated.h"

class USkeletalMeshComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnRuntimeResponseReceived, const FPromptMotionRuntimeResponse&, Response);

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

    /** 세션 식별자 */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Config")
    FString SessionId = TEXT("demo_session");

    /** 캐릭터 식별자 */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="PromptMotion|Config")
    FString CharacterId = TEXT("default_guide");

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

    // ------------------------------------------------------------------
    // 마지막 응답 캐시 (Blueprint 직접 참조용)
    // ------------------------------------------------------------------

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion|State")
    FString LastReply;

    UPROPERTY(BlueprintReadOnly, Category="PromptMotion|State")
    FPromptMotionBehavior LastBehavior;

    // ------------------------------------------------------------------
    // Blueprint 호출 함수
    // ------------------------------------------------------------------

    /** 메시지만 보낼 때. SceneContext는 빈 값으로 전송. */
    UFUNCTION(BlueprintCallable, Category="PromptMotion")
    void SendRuntimeMessage(const FString& Message);

    /** SceneContext 포함해서 보낼 때. */
    UFUNCTION(BlueprintCallable, Category="PromptMotion")
    void SendRuntimeMessageWithContext(const FString& Message, const FPromptMotionSceneContext& SceneContext);

    /**
     * emotion + intensity를 TargetMesh morph target에 직접 적용.
     * 응답 수신 시 자동 호출되며, Blueprint에서도 수동 호출 가능.
     */
    UFUNCTION(BlueprintCallable, Category="PromptMotion")
    void ApplyFacePreset(const FString& Emotion, float Intensity);

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    TUniquePtr<FPromptMotionApiClient> ApiClient;
    FString CachedBaseUrl;

    /** 진행 중인 요청 ID. SendRuntimeMessage마다 증가. 응답 수신 시 일치하지 않으면 무시. */
    FThreadSafeCounter RequestIdCounter;

    void EnsureApiClient();

    /** TargetMesh가 설정되어 있으면 반환, 없으면 Owner에서 자동 탐색. */
    USkeletalMeshComponent* ResolveTargetMesh() const;
};
