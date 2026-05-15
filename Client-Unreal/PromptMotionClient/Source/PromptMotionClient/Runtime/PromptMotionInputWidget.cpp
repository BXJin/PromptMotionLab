#include "PromptMotionInputWidget.h"
#include "PromptMotionRuntimeComponent.h"
#include "PromptMotionLog.h"
#include "Components/EditableTextBox.h"
#include "Components/Button.h"
#include "Components/TextBlock.h"

void UPromptMotionInputWidget::NativeConstruct()
{
    Super::NativeConstruct();

    if (SendButton)
        SendButton->OnClicked.AddDynamic(this, &UPromptMotionInputWidget::OnSendClicked);

    if (InputBox)
        InputBox->OnTextCommitted.AddDynamic(this, &UPromptMotionInputWidget::OnInputCommitted);
}

void UPromptMotionInputWidget::NativeDestruct()
{
    // 위젯 소멸 시 delegate 해제 — RuntimeComponent가 살아있어도 콜백 안 날아오도록
    if (UPromptMotionRuntimeComponent* Comp = RuntimeComponent.Get())
        Comp->OnRuntimeResponseReceived.RemoveDynamic(this, &UPromptMotionInputWidget::OnResponseReceived);

    Super::NativeDestruct();
}

void UPromptMotionInputWidget::SetRuntimeComponent(UPromptMotionRuntimeComponent* Component)
{
    // 이전 컴포넌트 delegate 해제
    if (UPromptMotionRuntimeComponent* Old = RuntimeComponent.Get())
        Old->OnRuntimeResponseReceived.RemoveDynamic(this, &UPromptMotionInputWidget::OnResponseReceived);

    RuntimeComponent = Component;

    if (Component)
        Component->OnRuntimeResponseReceived.AddDynamic(this, &UPromptMotionInputWidget::OnResponseReceived);
}

void UPromptMotionInputWidget::OnSendClicked()
{
    SubmitInput();
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
        UE_LOG(LogPromptMotion, Warning, TEXT("[InputWidget] RuntimeComponent not set — call SetRuntimeComponent first"));
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

void UPromptMotionInputWidget::SetSendEnabled(bool bEnabled)
{
    if (SendButton)
        SendButton->SetIsEnabled(bEnabled);

    if (InputBox)
        InputBox->SetIsEnabled(bEnabled);
}
