#include "Preview/PreviewSession.h"

bool FPreviewSession::ResolveTarget(
	const FString& RequestedSkeletonPreset,
	FPreviewTarget& OutTarget,
	FString& OutError) const
{
	return TargetResolver.ResolveSelectedActor(RequestedSkeletonPreset, OutTarget, OutError);
}

bool FPreviewSession::ApplyPreviewPlan(
	const FString& RequestedSkeletonPreset,
	const FProceduralGesture& Gesture,
	FString& OutPreviewSummary,
	FString& OutError) const
{
	FPreviewTarget Target;
	if (!ResolveTarget(RequestedSkeletonPreset, Target, OutError))
	{
		return false;
	}

	if (!MannyAdapter.SupportsTarget(Target))
	{
		OutError = FString::Printf(TEXT("No Control Rig adapter registered for '%s'."), *Target.SkeletonPreset);
		return false;
	}

	return MannyAdapter.BuildPreviewPlan(Target, Gesture, OutPreviewSummary, OutError);
}

