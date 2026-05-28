#include "PromptMotionInputWidget.h"

#include "PromptMotionLog.h"
#include "PromptMotionRuntimeComponent.h"
#include "Components/Button.h"
#include "Components/ComboBoxString.h"
#include "Components/EditableTextBox.h"
#include "Components/TextBlock.h"

namespace
{
FText VoiceStatusLabel(EPromptMotionVoiceStatus Status)
{
    switch (Status)
    {
    case EPromptMotionVoiceStatus::Idle:
        return FText::FromString(TEXT("Idle"));
    case EPromptMotionVoiceStatus::Listening:
        return FText::FromString(TEXT("Listening"));
    case EPromptMotionVoiceStatus::UserSpeaking:
        return FText::FromString(TEXT("Speaking"));
    case EPromptMotionVoiceStatus::Transcribing:
        return FText::FromString(TEXT("Transcribing"));
    case EPromptMotionVoiceStatus::Thinking:
        return FText::FromString(TEXT("Thinking"));
    case EPromptMotionVoiceStatus::CharacterSpeaking:
        return FText::FromString(TEXT("Character Speaking"));
    case EPromptMotionVoiceStatus::Cooldown:
        return FText::FromString(TEXT("Cooldown"));
    case EPromptMotionVoiceStatus::Error:
        return FText::FromString(TEXT("Error"));
    default:
        return FText::FromString(TEXT("Voice"));
    }
}

FLinearColor VoiceStatusColor(EPromptMotionVoiceStatus Status)
{
    switch (Status)
    {
    case EPromptMotionVoiceStatus::Listening:
        return FLinearColor(0.20f, 0.55f, 1.00f, 1.0f);
    case EPromptMotionVoiceStatus::UserSpeaking:
        return FLinearColor(0.15f, 0.85f, 0.35f, 1.0f);
    case EPromptMotionVoiceStatus::Transcribing:
        return FLinearColor(1.00f, 0.62f, 0.18f, 1.0f);
    case EPromptMotionVoiceStatus::Thinking:
        return FLinearColor(0.72f, 0.45f, 1.00f, 1.0f);
    case EPromptMotionVoiceStatus::CharacterSpeaking:
        return FLinearColor(0.20f, 0.95f, 1.00f, 1.0f);
    case EPromptMotionVoiceStatus::Error:
        return FLinearColor(1.00f, 0.20f, 0.20f, 1.0f);
    case EPromptMotionVoiceStatus::Cooldown:
    case EPromptMotionVoiceStatus::Idle:
    default:
        return FLinearColor(0.78f, 0.78f, 0.78f, 1.0f);
    }
}
}

void UPromptMotionInputWidget::NativeConstruct()
{
    Super::NativeConstruct();

    if (SendButton)
        SendButton->OnClicked.AddDynamic(this, &UPromptMotionInputWidget::OnSendClicked);

    if (MicButton)
    {
        MicButton->OnPressed.AddDynamic(this, &UPromptMotionInputWidget::OnMicPressed);
        MicButton->OnReleased.AddDynamic(this, &UPromptMotionInputWidget::OnMicReleased);
    }

    if (VadToggleButton)
        VadToggleButton->OnClicked.AddDynamic(this, &UPromptMotionInputWidget::OnVadToggleClicked);

    if (InputBox)
        InputBox->OnTextCommitted.AddDynamic(this, &UPromptMotionInputWidget::OnInputCommitted);

    if (PresetCombo)
        PresetCombo->OnSelectionChanged.AddDynamic(this, &UPromptMotionInputWidget::OnPresetSelectionChanged);

    SetVoiceStatusDisplay(EPromptMotionVoiceStatus::Idle);
    SetVadButtonDisplay();
}

void UPromptMotionInputWidget::NativeDestruct()
{
    if (UPromptMotionRuntimeComponent* Comp = RuntimeComponent.Get())
    {
        Comp->OnRuntimeResponseReceived.RemoveDynamic(this, &UPromptMotionInputWidget::OnResponseReceived);
        Comp->OnVoiceStatusChanged.RemoveDynamic(this, &UPromptMotionInputWidget::OnVoiceStatusChanged);
    }

    Super::NativeDestruct();
}

void UPromptMotionInputWidget::SetRuntimeComponent(UPromptMotionRuntimeComponent* Component)
{
    if (UPromptMotionRuntimeComponent* Old = RuntimeComponent.Get())
    {
        Old->OnRuntimeResponseReceived.RemoveDynamic(this, &UPromptMotionInputWidget::OnResponseReceived);
        Old->OnVoiceStatusChanged.RemoveDynamic(this, &UPromptMotionInputWidget::OnVoiceStatusChanged);
    }

    RuntimeComponent = Component;

    if (Component)
    {
        Component->OnRuntimeResponseReceived.AddDynamic(this, &UPromptMotionInputWidget::OnResponseReceived);
        Component->OnVoiceStatusChanged.AddDynamic(this, &UPromptMotionInputWidget::OnVoiceStatusChanged);

        if (PresetCombo)
        {
            PresetCombo->ClearOptions();
            for (const FString& Preset : Component->CharacterPresets)
                PresetCombo->AddOption(Preset);

            PresetCombo->SetSelectedOption(Component->CharacterId);
        }
    }

    SetVoiceStatusDisplay(EPromptMotionVoiceStatus::Idle);
    SetVadButtonDisplay();
}

void UPromptMotionInputWidget::OnSendClicked()
{
    SubmitInput();
}

void UPromptMotionInputWidget::OnMicPressed()
{
    UPromptMotionRuntimeComponent* Comp = RuntimeComponent.Get();
    if (!Comp)
        return;

    if (bVadEnabled)
    {
        bVadEnabled = false;
        Comp->SetVoiceVadEnabled(false);
        SetVadButtonDisplay();
    }

    Comp->StartPushToTalk();
}

void UPromptMotionInputWidget::OnMicReleased()
{
    if (UPromptMotionRuntimeComponent* Comp = RuntimeComponent.Get())
        Comp->StopPushToTalkAndSend();
}

void UPromptMotionInputWidget::OnVadToggleClicked()
{
    UPromptMotionRuntimeComponent* Comp = RuntimeComponent.Get();
    if (!Comp)
        return;

    bVadEnabled = !bVadEnabled;
    Comp->SetVoiceVadEnabled(bVadEnabled);
    SetVadButtonDisplay();
}

void UPromptMotionInputWidget::OnPresetSelectionChanged(FString SelectedItem, ESelectInfo::Type SelectionType)
{
    if (SelectionType == ESelectInfo::Direct)
        return;

    if (UPromptMotionRuntimeComponent* Comp = RuntimeComponent.Get())
    {
        UE_LOG(LogPromptMotion, Log, TEXT("[InputWidget] Preset: %s"), *SelectedItem);
        Comp->SetCharacterId(SelectedItem);
    }
}

void UPromptMotionInputWidget::OnInputCommitted(const FText& Text, ETextCommit::Type CommitMethod)
{
    if (CommitMethod == ETextCommit::OnEnter)
        SubmitInput();
}

void UPromptMotionInputWidget::SubmitInput()
{
    if (bPendingRequest)
        return;

    if (!InputBox)
        return;

    const FString Message = InputBox->GetText().ToString().TrimStartAndEnd();
    if (Message.IsEmpty())
        return;

    UPromptMotionRuntimeComponent* Comp = RuntimeComponent.Get();
    if (!Comp)
    {
        UE_LOG(LogPromptMotion, Warning, TEXT("[InputWidget] RuntimeComponent not set - call SetRuntimeComponent first"));
        return;
    }

    InputBox->SetText(FText::GetEmpty());
    SetSendEnabled(false);
    bPendingRequest = true;

    UE_LOG(LogPromptMotion, Log, TEXT("[InputWidget] Sending: \"%s\""), *Message);

    Comp->SendRuntimeMessage(Message);
}

void UPromptMotionInputWidget::OnResponseReceived(const FPromptMotionRuntimeResponse& Response)
{
    bPendingRequest = false;
    SetSendEnabled(true);

    if (ReplyText)
    {
        const FString Display = Response.bSuccess
            ? Response.Reply
            : FString::Printf(TEXT("[Error] %s"), *Response.ErrorMessage);

        ReplyText->SetText(FText::FromString(Display));
    }
}

void UPromptMotionInputWidget::OnVoiceStatusChanged(EPromptMotionVoiceStatus Status)
{
    SetVoiceStatusDisplay(Status);
}

void UPromptMotionInputWidget::SetSendEnabled(bool bEnabled)
{
    if (SendButton)
        SendButton->SetIsEnabled(bEnabled);

    if (InputBox)
        InputBox->SetIsEnabled(bEnabled);
}

void UPromptMotionInputWidget::SetVoiceStatusDisplay(EPromptMotionVoiceStatus Status)
{
    if (!VoiceStatusText)
        return;

    VoiceStatusText->SetText(VoiceStatusLabel(Status));
    VoiceStatusText->SetColorAndOpacity(FSlateColor(VoiceStatusColor(Status)));
}

void UPromptMotionInputWidget::SetVadButtonDisplay()
{
    if (!VadToggleButton)
        return;

    VadToggleButton->SetToolTipText(bVadEnabled
        ? FText::FromString(TEXT("VAD On"))
        : FText::FromString(TEXT("VAD Off")));
    VadToggleButton->SetRenderOpacity(bVadEnabled ? 1.0f : 0.55f);
}
