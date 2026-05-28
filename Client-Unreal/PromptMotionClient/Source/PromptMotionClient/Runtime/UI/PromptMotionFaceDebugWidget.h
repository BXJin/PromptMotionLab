#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "PromptMotionFaceDebugWidget.generated.h"

class UButton;
class UComboBoxString;
class UEditableTextBox;
class USlider;
class UPromptMotionRuntimeComponent;

/**
 * 표정/립싱크 디버그 위젯 (WBP 기반).
 *
 * WBP에서 아래 이름으로 위젯을 추가하면 자동 연결됨:
 *
 *  [Face Preset 섹션]
 *    PresetComboBox      : ComboBoxString  — 표정 프리셋 선택
 *    FaceMorphComboBox   : ComboBoxString  — morph target 선택
 *    FaceWeightSlider    : Slider          — weight 미리보기
 *    FaceWeightTextBox   : EditableTextBox — weight 직접 입력
 *    ApplyFaceButton     : Button          — 선택 morph에 weight 즉시 적용
 *    SaveFaceButton      : Button          — 현재 값 CSV에 저장
 *
 *  [LipSync Viseme 섹션]
 *    VisemeIdComboBox    : ComboBoxString  — viseme ID 선택 (0~21)
 *    VisemeMorphComboBox : ComboBoxString  — morph target 선택
 *    VisemeWeightSlider  : Slider
 *    VisemeWeightTextBox : EditableTextBox
 *    ApplyVisemeButton   : Button          — 선택 viseme 적용
 *    SaveVisemeButton    : Button          — 현재 값 CSV에 저장
 *
 *  [공통]
 *    ReloadButton        : Button          — CSV 리로드
 */
UCLASS(Abstract)
class PROMPTMOTIONCLIENT_API UPromptMotionFaceDebugWidget : public UUserWidget
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category="PromptMotion|Debug")
    void SetRuntimeComponent(UPromptMotionRuntimeComponent* InRuntimeComponent);

protected:
    virtual void NativeConstruct() override;

    // ------------------------------------------------------------------
    // BindWidget — WBP에서 이름 정확히 일치시킬 것
    // ------------------------------------------------------------------

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UButton> ReloadButton;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UComboBoxString> PresetComboBox;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UComboBoxString> FaceMorphComboBox;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<USlider> FaceWeightSlider;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UEditableTextBox> FaceWeightTextBox;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UButton> ApplyFaceButton;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UButton> SaveFaceButton;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UComboBoxString> VisemeIdComboBox;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UComboBoxString> VisemeMorphComboBox;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<USlider> VisemeWeightSlider;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UEditableTextBox> VisemeWeightTextBox;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UButton> ApplyVisemeButton;

    UPROPERTY(meta=(BindWidgetOptional))
    TObjectPtr<UButton> SaveVisemeButton;

private:
    UPROPERTY()
    TObjectPtr<UPromptMotionRuntimeComponent> RuntimeComponent;

    UFUNCTION()
    void HandleReloadClicked();

    UFUNCTION()
    void HandleApplyMorphClicked();

    UFUNCTION()
    void HandleSaveFacePresetClicked();

    UFUNCTION()
    void HandleApplyVisemeClicked();

    UFUNCTION()
    void HandleSaveVisemeClicked();

    UFUNCTION()
    void HandleFaceWeightChanged(float Value);

    UFUNCTION()
    void HandleVisemeWeightChanged(float Value);

    // Preset/VisemeId 변경 → CSV 값으로 weight 초기화 + 미리보기
    UFUNCTION()
    void HandlePresetSelectionChanged(FString SelectedItem, ESelectInfo::Type SelectionType);

    UFUNCTION()
    void HandleVisemeIdSelectionChanged(FString SelectedItem, ESelectInfo::Type SelectionType);

    // Morph 변경 → 현재 슬라이더 값 유지, 미리보기만
    UFUNCTION()
    void HandleFaceMorphSelectionChanged(FString SelectedItem, ESelectInfo::Type SelectionType);

    UFUNCTION()
    void HandleVisemeMorphSelectionChanged(FString SelectedItem, ESelectInfo::Type SelectionType);

    // 모프별 마지막 설정값 기억 — Preset/VisemeId 바꾸면 초기화
    TMap<FName, float> UserFaceWeights;
    TMap<FName, float> UserVisemeWeights;

    void UpdateFaceWeightDisplay();
    void UpdateVisemeWeightDisplay();
    void SetFaceWeightDisplay(float Value);
    void SetVisemeWeightDisplay(float Value);
    void PreviewSelectedFacePreset();
    void PreviewSelectedViseme();
    void ReapplyAllUserFaceWeights();
    void ReapplyAllUserVisemeWeights();

    FString GetSelectedOption(UComboBoxString* ComboBox) const;
    float GetTextWeight(UEditableTextBox* TextBox, USlider* FallbackSlider) const;
};
