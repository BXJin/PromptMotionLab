#pragma once

#include "CoreMinimal.h"
#include "Core/MotionGenerationClient.h"
#include "Preview/PreviewSession.h"
#include "Widgets/SCompoundWidget.h"

class SEditableTextBox;
class SMultiLineEditableTextBox;
class STextBlock;

class SMotionLabPanel final : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SMotionLabPanel) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

private:
	FReply OnGenerateProceduralClicked();
	FReply OnGenerateEnrichedPromptClicked();
	FReply OnResolveTargetClicked();
	FReply OnApplyPreviewClicked();

	void SetStatus(const FString& Message);
	FString GetPromptText() const;
	FString GetServerUrl() const;
	FString GetSkeletonPreset() const;
	void ShowProceduralResult(const FProceduralGenerationResult& Result);
	void ShowEnrichedPromptResult(const FEnrichedPromptResult& Result);

private:
	TSharedPtr<FMotionGenerationClient> Client;
	TSharedPtr<FPreviewSession> PreviewSession;
	TSharedPtr<SEditableTextBox> ServerUrlTextBox;
	TSharedPtr<SEditableTextBox> SkeletonPresetTextBox;
	TSharedPtr<SMultiLineEditableTextBox> PromptTextBox;
	TSharedPtr<SMultiLineEditableTextBox> OutputTextBox;
	TSharedPtr<STextBlock> StatusTextBlock;
	FProceduralGenerationResult LastProceduralResult;
	bool bHasProceduralResult = false;
};
