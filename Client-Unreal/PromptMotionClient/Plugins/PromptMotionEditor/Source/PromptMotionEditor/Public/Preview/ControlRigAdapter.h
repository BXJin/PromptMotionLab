#pragma once

#include "CoreMinimal.h"
#include "Data/PromptMotionTypes.h"
#include "Preview/PreviewTarget.h"

class IControlRigAdapter
{
public:
	virtual ~IControlRigAdapter() = default;

	virtual bool SupportsTarget(const FPreviewTarget& Target) const = 0;
	virtual bool BuildPreviewPlan(
		const FPreviewTarget& Target,
		const FProceduralGesture& Gesture,
		FString& OutPreviewPlan,
		FString& OutError) const = 0;
};

