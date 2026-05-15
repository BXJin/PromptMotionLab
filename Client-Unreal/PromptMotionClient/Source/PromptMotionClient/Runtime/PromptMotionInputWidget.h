#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "PromptMotionTypes.h"
#include "PromptMotionInputWidget.generated.h"

class UEditableTextBox;
class UButton;
class UTextBlock;
class UPromptMotionRuntimeComponent;

/**
 * 텍스트 입력 → PromptMotionRuntimeComponent 전송 UI.
 *
 * 사용법:
 *   1. 이 클래스를 부모로 하는 Widget Blueprint(WBP_PromptMotionInput) 생성.
 *   2. WBP에 다음 이름으로 위젯 추가 (BindWidget — 이름 정확히 일치해야 함):
 *        - InputBox    : EditableTextBox
 *        - SendButton  : Button
 *        - ReplyText   : TextBlock  (없어도 컴파일 가능 — meta=BindWidgetOptional)
 *   3. BP_ThirdPersonCharacter BeginPlay에서:
 *        - CreateWidget → Add to Viewport
 *        - SetRuntimeComponent(PromptMotionRuntimeComponent ref)
 *
 * 동작:
 *   - SendButton 클릭 or InputBox에서 Enter → SendRuntimeMessage 호출
 *   - 전송 후 InputBox 초기화
 *   - 서버 응답 수신 시 ReplyText 업데이트 (Optional)
 *   - 전송 중 SendButton 비활성화 → 응답 수신/실패 시 재활성화 (중복 전송 방지)
 */
UCLASS(Abstract)
class PROMPTMOTIONCLIENT_API UPromptMotionInputWidget : public UUserWidget
{
    GENERATED_BODY()

public:
    /** BP_ThirdPersonCharacter BeginPlay에서 호출해 컴포넌트 연결. */
    UFUNCTION(BlueprintCallable, Category="PromptMotion")
    void SetRuntimeComponent(UPromptMotionRuntimeComponent* Component);

protected:
    // ------------------------------------------------------------------
    // BindWidget — WBP에서 이름 정확히 일치시킬 것
    // ------------------------------------------------------------------

    UPROPERTY(meta=(BindWidget))
    TObjectPtr<UEditableTextBox> InputBox;

    UPROPERTY(meta=(BindWidget))
    TObjectPtr<UButton> SendButton;

    /** 선택적. WBP에 없어도 빌드 가능. */
    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UTextBlock> ReplyText;

    // ------------------------------------------------------------------
    // UUserWidget overrides
    // ------------------------------------------------------------------

    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;

private:
    TWeakObjectPtr<UPromptMotionRuntimeComponent> RuntimeComponent;

    /** 진행 중인 요청이 있으면 true — 중복 전송 방지용 */
    bool bPendingRequest = false;

    UFUNCTION()
    void OnSendClicked();

    UFUNCTION()
    void OnInputCommitted(const FText& Text, ETextCommit::Type CommitMethod);

    UFUNCTION()
    void OnResponseReceived(const FPromptMotionRuntimeResponse& Response);

    void SubmitInput();
    void SetSendEnabled(bool bEnabled);
};
