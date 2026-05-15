#pragma once

#include "Preview/ControlRigAdapter.h"

class FMannyControlRigAdapter final : public IControlRigAdapter
{
public:
	virtual bool SupportsTarget(const FPreviewTarget& Target) const override;
	virtual bool BuildPreviewPlan(
		const FPreviewTarget& Target,
		const FProceduralGesture& Gesture,
		FString& OutPreviewPlan,
		FString& OutError) const override;
};

