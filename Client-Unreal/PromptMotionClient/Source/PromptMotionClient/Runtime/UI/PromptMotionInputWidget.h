#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "PromptMotionRuntimeComponent.h"
#include "PromptMotionTypes.h"
#include "PromptMotionInputWidget.generated.h"

class UButton;
class UComboBoxString;
class UEditableTextBox;
class UTextBlock;
class UPromptMotionRuntimeComponent;

// Text and voice input widget for PromptMotionRuntimeComponent.
// Optional widgets are used by the mobile/debug layouts when present.
UCLASS(Abstract)
class PROMPTMOTIONCLIENT_API UPromptMotionInputWidget : public UUserWidget
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category="PromptMotion")
    void SetRuntimeComponent(UPromptMotionRuntimeComponent* Component);

protected:
    UPROPERTY(meta=(BindWidget))
    TObjectPtr<UEditableTextBox> InputBox;

    UPROPERTY(meta=(BindWidget))
    TObjectPtr<UButton> SendButton;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UTextBlock> ReplyText;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UComboBoxString> PresetCombo;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UButton> MicButton;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UButton> VadToggleButton;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UTextBlock> VoiceStatusText;

    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;

private:
    TWeakObjectPtr<UPromptMotionRuntimeComponent> RuntimeComponent;

    bool bPendingRequest = false;
    bool bVadEnabled = false;

    UFUNCTION()
    void OnSendClicked();

    UFUNCTION()
    void OnMicPressed();

    UFUNCTION()
    void OnMicReleased();

    UFUNCTION()
    void OnVadToggleClicked();

    UFUNCTION()
    void OnPresetSelectionChanged(FString SelectedItem, ESelectInfo::Type SelectionType);

    UFUNCTION()
    void OnInputCommitted(const FText& Text, ETextCommit::Type CommitMethod);

    UFUNCTION()
    void OnResponseReceived(const FPromptMotionRuntimeResponse& Response);

    UFUNCTION()
    void OnVoiceStatusChanged(EPromptMotionVoiceStatus Status);

    void SubmitInput();
    void SetSendEnabled(bool bEnabled);
    void SetVoiceStatusDisplay(EPromptMotionVoiceStatus Status);
    void SetVadButtonDisplay();
};
