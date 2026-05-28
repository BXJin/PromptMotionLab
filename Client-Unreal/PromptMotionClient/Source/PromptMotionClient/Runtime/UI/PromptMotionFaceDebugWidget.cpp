#include "PromptMotionFaceDebugWidget.h"

#include "Components/Button.h"
#include "Components/ComboBoxString.h"
#include "Components/EditableTextBox.h"
#include "Components/Slider.h"
#include "FaceMorphDomains.h"
#include "PromptMotionRuntimeComponent.h"

namespace
{
TArray<FString> SortedNamesFromSet(const TSet<FName>& Names)
{
    TArray<FString> Result;
    for (const FName& Name : Names)
        Result.Add(Name.ToString());
    Result.Sort();
    return Result;
}
}

void UPromptMotionFaceDebugWidget::SetRuntimeComponent(UPromptMotionRuntimeComponent* InRuntimeComponent)
{
    RuntimeComponent = InRuntimeComponent;
    UpdateFaceWeightDisplay();
    UpdateVisemeWeightDisplay();
}

void UPromptMotionFaceDebugWidget::NativeConstruct()
{
    Super::NativeConstruct();

    // ------------------------------------------------------------------
    // 버튼 delegate 바인딩
    // ------------------------------------------------------------------
    if (ReloadButton)
        ReloadButton->OnClicked.AddDynamic(this, &UPromptMotionFaceDebugWidget::HandleReloadClicked);

    if (ApplyFaceButton)
        ApplyFaceButton->OnClicked.AddDynamic(this, &UPromptMotionFaceDebugWidget::HandleApplyMorphClicked);

    if (SaveFaceButton)
        SaveFaceButton->OnClicked.AddDynamic(this, &UPromptMotionFaceDebugWidget::HandleSaveFacePresetClicked);

    if (ApplyVisemeButton)
        ApplyVisemeButton->OnClicked.AddDynamic(this, &UPromptMotionFaceDebugWidget::HandleApplyVisemeClicked);

    if (SaveVisemeButton)
        SaveVisemeButton->OnClicked.AddDynamic(this, &UPromptMotionFaceDebugWidget::HandleSaveVisemeClicked);

    // ------------------------------------------------------------------
    // 슬라이더 delegate 바인딩
    // ------------------------------------------------------------------
    if (FaceWeightSlider)
        FaceWeightSlider->OnValueChanged.AddDynamic(this, &UPromptMotionFaceDebugWidget::HandleFaceWeightChanged);

    if (VisemeWeightSlider)
        VisemeWeightSlider->OnValueChanged.AddDynamic(this, &UPromptMotionFaceDebugWidget::HandleVisemeWeightChanged);

    // ------------------------------------------------------------------
    // 콤보박스 delegate 바인딩
    // ------------------------------------------------------------------
    if (PresetComboBox)
        PresetComboBox->OnSelectionChanged.AddDynamic(this, &UPromptMotionFaceDebugWidget::HandlePresetSelectionChanged);

    if (FaceMorphComboBox)
        FaceMorphComboBox->OnSelectionChanged.AddDynamic(this, &UPromptMotionFaceDebugWidget::HandleFaceMorphSelectionChanged);

    if (VisemeIdComboBox)
        VisemeIdComboBox->OnSelectionChanged.AddDynamic(this, &UPromptMotionFaceDebugWidget::HandleVisemeIdSelectionChanged);

    if (VisemeMorphComboBox)
        VisemeMorphComboBox->OnSelectionChanged.AddDynamic(this, &UPromptMotionFaceDebugWidget::HandleVisemeMorphSelectionChanged);

    // ------------------------------------------------------------------
    // 콤보박스 옵션 초기화
    // ------------------------------------------------------------------
    if (PresetComboBox && PresetComboBox->GetOptionCount() == 0)
    {
        for (const FString& Preset : {
            TEXT("Neutral"), TEXT("Friendly"), TEXT("Happy"), TEXT("Thinking"),
            TEXT("Curious"), TEXT("Concerned"), TEXT("Uncertain"), TEXT("Apologetic"),
            TEXT("Listening"), TEXT("Explaining"), TEXT("Surprised") })
        {
            PresetComboBox->AddOption(Preset);
        }
        PresetComboBox->SetSelectedOption(TEXT("Friendly"));
    }

    if (FaceMorphComboBox && FaceMorphComboBox->GetOptionCount() == 0)
    {
        for (const FString& Name : SortedNamesFromSet(FFaceMorphDomains::Expression()))
            FaceMorphComboBox->AddOption(Name);
        FaceMorphComboBox->SetSelectedOption(TEXT("Eye_Squint_L"));
    }

    if (VisemeIdComboBox && VisemeIdComboBox->GetOptionCount() == 0)
    {
        for (int32 Id = 0; Id <= 21; ++Id)
            VisemeIdComboBox->AddOption(FString::FromInt(Id));
        VisemeIdComboBox->SetSelectedOption(TEXT("1"));
    }

    if (VisemeMorphComboBox && VisemeMorphComboBox->GetOptionCount() == 0)
    {
        for (const FString& Name : SortedNamesFromSet(FFaceMorphDomains::LipSync()))
            VisemeMorphComboBox->AddOption(Name);
        VisemeMorphComboBox->SetSelectedOption(TEXT("Mouth_Close"));
    }
}

void UPromptMotionFaceDebugWidget::HandleReloadClicked()
{
    if (!RuntimeComponent)
        return;

    RuntimeComponent->ReloadFaceConfig();
    PreviewSelectedFacePreset();
}

void UPromptMotionFaceDebugWidget::HandleApplyMorphClicked()
{
    if (!RuntimeComponent || !FaceMorphComboBox)
        return;

    RuntimeComponent->ApplyDebugMorph(
        FName(*GetSelectedOption(FaceMorphComboBox)),
        GetTextWeight(FaceWeightTextBox, FaceWeightSlider));
}

void UPromptMotionFaceDebugWidget::HandleSaveFacePresetClicked()
{
    if (!RuntimeComponent || !PresetComboBox || !FaceMorphComboBox)
        return;

    RuntimeComponent->SaveDebugFacePresetWeight(
        GetSelectedOption(PresetComboBox),
        FName(*GetSelectedOption(FaceMorphComboBox)),
        GetTextWeight(FaceWeightTextBox, FaceWeightSlider));
}

void UPromptMotionFaceDebugWidget::HandleApplyVisemeClicked()
{
    if (!RuntimeComponent || !VisemeIdComboBox)
        return;

    RuntimeComponent->ApplyDebugViseme(
        FCString::Atoi(*GetSelectedOption(VisemeIdComboBox)), 1.0f);
}

void UPromptMotionFaceDebugWidget::HandleSaveVisemeClicked()
{
    if (!RuntimeComponent || !VisemeIdComboBox || !VisemeMorphComboBox)
        return;

    RuntimeComponent->SaveDebugLipSyncVisemeWeight(
        FCString::Atoi(*GetSelectedOption(VisemeIdComboBox)),
        FName(*GetSelectedOption(VisemeMorphComboBox)),
        GetTextWeight(VisemeWeightTextBox, VisemeWeightSlider));
}

void UPromptMotionFaceDebugWidget::HandleFaceWeightChanged(float Value)
{
    if (FaceWeightTextBox)
        FaceWeightTextBox->SetText(FText::FromString(FString::Printf(TEXT("%.2f"), Value)));

    if (FaceMorphComboBox)
        UserFaceWeights.FindOrAdd(FName(*GetSelectedOption(FaceMorphComboBox))) = Value;

    if (RuntimeComponent && FaceMorphComboBox)
        RuntimeComponent->ApplyDebugMorph(FName(*GetSelectedOption(FaceMorphComboBox)), Value);
}

void UPromptMotionFaceDebugWidget::HandleVisemeWeightChanged(float Value)
{
    if (VisemeWeightTextBox)
        VisemeWeightTextBox->SetText(FText::FromString(FString::Printf(TEXT("%.2f"), Value)));

    if (VisemeMorphComboBox)
        UserVisemeWeights.FindOrAdd(FName(*GetSelectedOption(VisemeMorphComboBox))) = Value;

    if (RuntimeComponent && VisemeMorphComboBox)
        RuntimeComponent->ApplyDebugMorph(FName(*GetSelectedOption(VisemeMorphComboBox)), Value);
}

void UPromptMotionFaceDebugWidget::HandlePresetSelectionChanged(FString SelectedItem, ESelectInfo::Type SelectionType)
{
    UserFaceWeights.Empty();     // Preset 전환 → 모프별 기억값 초기화
    UpdateFaceWeightDisplay();   // CSV 저장값으로 슬라이더 리셋
    PreviewSelectedFacePreset();
}

void UPromptMotionFaceDebugWidget::HandleFaceMorphSelectionChanged(FString SelectedItem, ESelectInfo::Type SelectionType)
{
    // 슬라이더: 이 모프에 기억된 값 복원, 없으면 CSV 값
    const FName MorphName(*SelectedItem);
    if (const float* Saved = UserFaceWeights.Find(MorphName))
        SetFaceWeightDisplay(*Saved);
    else
        UpdateFaceWeightDisplay();

    // preset 전체 리셋 없이 지금까지 저장된 조정값들만 재적용
    ReapplyAllUserFaceWeights();
}

void UPromptMotionFaceDebugWidget::HandleVisemeIdSelectionChanged(FString SelectedItem, ESelectInfo::Type SelectionType)
{
    UserVisemeWeights.Empty();   // VisemeId 전환 → 모프별 기억값 초기화
    UpdateVisemeWeightDisplay(); // CSV 저장값으로 슬라이더 리셋
    PreviewSelectedViseme();
}

void UPromptMotionFaceDebugWidget::HandleVisemeMorphSelectionChanged(FString SelectedItem, ESelectInfo::Type SelectionType)
{
    const FName MorphName(*SelectedItem);
    if (const float* Saved = UserVisemeWeights.Find(MorphName))
        SetVisemeWeightDisplay(*Saved);
    else
        UpdateVisemeWeightDisplay();

    ReapplyAllUserVisemeWeights();
}

void UPromptMotionFaceDebugWidget::UpdateFaceWeightDisplay()
{
    if (!RuntimeComponent || !PresetComboBox || !FaceMorphComboBox)
        return;

    const float Weight = RuntimeComponent->QueryDebugFaceWeight(
        GetSelectedOption(PresetComboBox),
        FName(*GetSelectedOption(FaceMorphComboBox)));

    SetFaceWeightDisplay(Weight);
}

void UPromptMotionFaceDebugWidget::UpdateVisemeWeightDisplay()
{
    if (!RuntimeComponent || !VisemeIdComboBox || !VisemeMorphComboBox)
        return;

    const float Weight = RuntimeComponent->QueryDebugVisemeWeight(
        FCString::Atoi(*GetSelectedOption(VisemeIdComboBox)),
        FName(*GetSelectedOption(VisemeMorphComboBox)));

    SetVisemeWeightDisplay(Weight);
}

void UPromptMotionFaceDebugWidget::SetFaceWeightDisplay(float Value)
{
    if (FaceWeightSlider)
    {
        FaceWeightSlider->SetMinValue(-1.0f);
        FaceWeightSlider->SetValue(Value);
    }
    if (FaceWeightTextBox)
        FaceWeightTextBox->SetText(FText::FromString(FString::Printf(TEXT("%.2f"), Value)));
}

void UPromptMotionFaceDebugWidget::SetVisemeWeightDisplay(float Value)
{
    if (VisemeWeightSlider)
    {
        VisemeWeightSlider->SetMinValue(-1.0f);
        VisemeWeightSlider->SetValue(Value);
    }
    if (VisemeWeightTextBox)
        VisemeWeightTextBox->SetText(FText::FromString(FString::Printf(TEXT("%.2f"), Value)));
}

void UPromptMotionFaceDebugWidget::PreviewSelectedFacePreset()
{
    if (!RuntimeComponent || !PresetComboBox)
        return;

    RuntimeComponent->ApplyFacePreset(GetSelectedOption(PresetComboBox), 1.0f);
}

void UPromptMotionFaceDebugWidget::PreviewSelectedViseme()
{
    if (!RuntimeComponent || !VisemeIdComboBox)
        return;

    RuntimeComponent->ApplyDebugViseme(
        FCString::Atoi(*GetSelectedOption(VisemeIdComboBox)), 1.0f);
}

void UPromptMotionFaceDebugWidget::ReapplyAllUserFaceWeights()
{
    if (!RuntimeComponent)
        return;
    for (const auto& Pair : UserFaceWeights)
        RuntimeComponent->ApplyDebugMorph(Pair.Key, Pair.Value);
}

void UPromptMotionFaceDebugWidget::ReapplyAllUserVisemeWeights()
{
    if (!RuntimeComponent)
        return;
    for (const auto& Pair : UserVisemeWeights)
        RuntimeComponent->ApplyDebugMorph(Pair.Key, Pair.Value);
}

FString UPromptMotionFaceDebugWidget::GetSelectedOption(UComboBoxString* ComboBox) const
{
    return ComboBox ? ComboBox->GetSelectedOption() : FString();
}

float UPromptMotionFaceDebugWidget::GetTextWeight(UEditableTextBox* TextBox, USlider* FallbackSlider) const
{
    if (TextBox)
    {
        const FString Text = TextBox->GetText().ToString();
        if (Text.IsNumeric())
            return FMath::Clamp(FCString::Atof(*Text), -1.0f, 1.0f);
    }
    return FallbackSlider ? FMath::Clamp(FallbackSlider->GetValue(), -1.0f, 1.0f) : 0.0f;
}
