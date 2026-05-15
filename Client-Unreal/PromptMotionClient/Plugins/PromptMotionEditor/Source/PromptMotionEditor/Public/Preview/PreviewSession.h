#pragma once

#include "CoreMinimal.h"
#include "Data/PromptMotionTypes.h"
#include "Preview/MannyControlRigAdapter.h"
#include "Preview/PreviewTargetResolver.h"

class FPreviewSession
{
public:
	bool ResolveTarget(const FString& RequestedSkeletonPreset, FPreviewTarget& OutTarget, FString& OutError) const;
	bool ApplyPreviewPlan(
		const FString& RequestedSkeletonPreset,
		const FProceduralGesture& Gesture,
		FString& OutPreviewSummary,
		FString& OutError) const;

private:
	FPreviewTargetResolver TargetResolver;
	FMannyControlRigAdapter MannyAdapter;
};

