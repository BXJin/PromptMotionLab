#include "UI/SMotionLabPanel.h"

#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "SMotionLabPanel"

void SMotionLabPanel::Construct(const FArguments& InArgs)
{
	Client = MakeShared<FMotionGenerationClient>();
	PreviewSession = MakeShared<FPreviewSession>();

	ChildSlot
	[
		SNew(SScrollBox)
		+ SScrollBox::Slot()
		.Padding(12.0f)
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 8.0f)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("Title", "Prompt Motion Lab"))
				.Font(FCoreStyle::GetDefaultFontStyle("Bold", 18))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 8.0f)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("ServerUrlLabel", "Server URL"))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 12.0f)
			[
				SAssignNew(ServerUrlTextBox, SEditableTextBox)
				.Text(FText::FromString(TEXT("http://127.0.0.1:8010")))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 8.0f)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("SkeletonPresetLabel", "Skeleton Preset"))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 12.0f)
			[
				SAssignNew(SkeletonPresetTextBox, SEditableTextBox)
				.Text(FText::FromString(TEXT("ue5_manny")))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 8.0f)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("PromptLabel", "Prompt"))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.MinHeight(96.0f)
			.Padding(0.0f, 0.0f, 0.0f, 12.0f)
			[
				SAssignNew(PromptTextBox, SMultiLineEditableTextBox)
				.Text(FText::FromString(TEXT("웃으면서 오른손으로 손 흔들어줘")))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 12.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 8.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("GenerateProceduralButton", "Generate Procedural"))
					.OnClicked(this, &SMotionLabPanel::OnGenerateProceduralClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 8.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("GenerateEnrichedButton", "Generate Enriched Prompt"))
					.OnClicked(this, &SMotionLabPanel::OnGenerateEnrichedPromptClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 8.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("ResolveTargetButton", "Resolve Target"))
					.OnClicked(this, &SMotionLabPanel::OnResolveTargetClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SButton)
					.Text(LOCTEXT("ApplyPreviewButton", "Apply Preview"))
					.OnClicked(this, &SMotionLabPanel::OnApplyPreviewClicked)
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 8.0f)
			[
				SAssignNew(StatusTextBlock, STextBlock)
				.Text(LOCTEXT("ReadyStatus", "Ready"))
			]

			+ SVerticalBox::Slot()
			.FillHeight(1.0f)
			.MinHeight(260.0f)
			[
				SAssignNew(OutputTextBox, SMultiLineEditableTextBox)
				.IsReadOnly(true)
			]
		]
	];
}

FReply SMotionLabPanel::OnGenerateProceduralClicked()
{
	SetStatus(TEXT("Requesting procedural gesture..."));
	OutputTextBox->SetText(FText::GetEmpty());

	Client->GenerateProcedural(
		GetServerUrl(),
		GetPromptText(),
		GetSkeletonPreset(),
		[this](bool bSuccess, const FProceduralGenerationResult& Result, const FString& ErrorMessage)
		{
			if (!bSuccess)
			{
				SetStatus(ErrorMessage);
				return;
			}

			SetStatus(TEXT("Procedural gesture generated."));
			LastProceduralResult = Result;
			bHasProceduralResult = true;
			ShowProceduralResult(Result);
		});

	return FReply::Handled();
}

FReply SMotionLabPanel::OnResolveTargetClicked()
{
	FPreviewTarget Target;
	FString Error;
	if (!PreviewSession->ResolveTarget(GetSkeletonPreset(), Target, Error))
	{
		SetStatus(Error);
		return FReply::Handled();
	}

	SetStatus(TEXT("Preview target resolved."));
	const FString Summary = FString::Printf(
		TEXT("Preview Target\n")
		TEXT("  target: %s\n")
		TEXT("  skeletonPreset: %s\n\n")
		TEXT("  skeleton: %s\n\n")
		TEXT("This target can be used by the Manny Control Rig adapter."),
		*Target.DisplayName,
		*Target.SkeletonPreset,
		*Target.SkeletonPath);
	OutputTextBox->SetText(FText::FromString(Summary));
	return FReply::Handled();
}

FReply SMotionLabPanel::OnApplyPreviewClicked()
{
	if (!bHasProceduralResult)
	{
		SetStatus(TEXT("Generate Procedural before applying preview."));
		return FReply::Handled();
	}

	FString PreviewSummary;
	FString Error;
	if (!PreviewSession->ApplyPreviewPlan(
		GetSkeletonPreset(),
		LastProceduralResult.ProceduralGesture,
		PreviewSummary,
		Error))
	{
		SetStatus(Error);
		return FReply::Handled();
	}

	SetStatus(TEXT("Preview plan built for selected Actor."));
	OutputTextBox->SetText(FText::FromString(PreviewSummary));
	return FReply::Handled();
}

FReply SMotionLabPanel::OnGenerateEnrichedPromptClicked()
{
	SetStatus(TEXT("Requesting enriched prompt..."));
	OutputTextBox->SetText(FText::GetEmpty());

	Client->GenerateEnrichedPrompt(
		GetServerUrl(),
		GetPromptText(),
		GetSkeletonPreset(),
		[this](bool bSuccess, const FEnrichedPromptResult& Result, const FString& ErrorMessage)
		{
			if (!bSuccess)
			{
				SetStatus(ErrorMessage);
				return;
			}

			SetStatus(TEXT("Enriched prompt generated and exported."));
			ShowEnrichedPromptResult(Result);
		});

	return FReply::Handled();
}

void SMotionLabPanel::SetStatus(const FString& Message)
{
	if (StatusTextBlock.IsValid())
	{
		StatusTextBlock->SetText(FText::FromString(Message));
	}
}

FString SMotionLabPanel::GetPromptText() const
{
	return PromptTextBox.IsValid() ? PromptTextBox->GetText().ToString() : FString();
}

FString SMotionLabPanel::GetServerUrl() const
{
	return ServerUrlTextBox.IsValid() ? ServerUrlTextBox->GetText().ToString() : FString(TEXT("http://127.0.0.1:8010"));
}

FString SMotionLabPanel::GetSkeletonPreset() const
{
	return SkeletonPresetTextBox.IsValid() ? SkeletonPresetTextBox->GetText().ToString() : FString(TEXT("ue5_manny"));
}

void SMotionLabPanel::ShowProceduralResult(const FProceduralGenerationResult& Result)
{
	const FString Summary = FString::Printf(
		TEXT("MotionSpec\n")
		TEXT("  gesture: %s\n")
		TEXT("  hand: %s\n")
		TEXT("  emotion: %s\n")
		TEXT("  skeletonPreset: %s\n\n")
		TEXT("ProceduralGesture\n")
		TEXT("  durationSeconds: %.2f\n")
		TEXT("  speed: %.2f\n")
		TEXT("  amplitude: %.2f\n")
		TEXT("  shoulderRaise: %.2f\n")
		TEXT("  elbowBend: %.2f\n")
		TEXT("  wristOscillation: %.2f\n\n")
		TEXT("Raw JSON\n%s"),
		*Result.MotionSpec.Gesture,
		*Result.MotionSpec.Hand,
		*Result.MotionSpec.Emotion,
		*Result.MotionSpec.SkeletonPreset,
		Result.ProceduralGesture.DurationSeconds,
		Result.ProceduralGesture.Speed,
		Result.ProceduralGesture.Amplitude,
		Result.ProceduralGesture.ShoulderRaise,
		Result.ProceduralGesture.ElbowBend,
		Result.ProceduralGesture.WristOscillation,
		*Result.RawJson);

	OutputTextBox->SetText(FText::FromString(Summary));
}

void SMotionLabPanel::ShowEnrichedPromptResult(const FEnrichedPromptResult& Result)
{
	const FString Summary = FString::Printf(
		TEXT("Prompt Export\n")
		TEXT("  exportId: %s\n")
		TEXT("  targetProviderHint: %s\n")
		TEXT("  createdAtUtc: %s\n\n")
		TEXT("Original Prompt\n%s\n\n")
		TEXT("Enriched Prompt\n%s\n\n")
		TEXT("Raw JSON\n%s"),
		*Result.Export.ExportId,
		*Result.Export.TargetProviderHint,
		*Result.Export.CreatedAtUtc,
		*Result.Export.OriginalPrompt,
		*Result.Export.EnrichedPrompt,
		*Result.RawJson);

	OutputTextBox->SetText(FText::FromString(Summary));
}

#undef LOCTEXT_NAMESPACE
