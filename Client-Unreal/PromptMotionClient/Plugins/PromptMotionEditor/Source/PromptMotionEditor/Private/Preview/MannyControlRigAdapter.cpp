#include "Preview/MannyControlRigAdapter.h"

#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Actor.h"

bool FMannyControlRigAdapter::SupportsTarget(const FPreviewTarget& Target) const
{
	return Target.IsValid() && Target.SkeletonPreset.Equals(TEXT("ue5_manny"), ESearchCase::IgnoreCase);
}

bool FMannyControlRigAdapter::BuildPreviewPlan(
	const FPreviewTarget& Target,
	const FProceduralGesture& Gesture,
	FString& OutPreviewPlan,
	FString& OutError) const
{
	if (!SupportsTarget(Target))
	{
		OutError = TEXT("MannyControlRigAdapter only supports ue5_manny targets.");
		return false;
	}

	if (!Gesture.Gesture.Equals(TEXT("wave"), ESearchCase::IgnoreCase))
	{
		OutError = FString::Printf(TEXT("Gesture '%s' is not implemented for Manny preview yet."), *Gesture.Gesture);
		return false;
	}

	const AActor* Actor = Target.Actor.Get();
	const USkeletalMeshComponent* MeshComponent = Target.SkeletalMeshComponent.Get();

	OutPreviewPlan = FString::Printf(
		TEXT("Preview target resolved\n")
		TEXT("  Actor: %s\n")
		TEXT("  SkeletalMeshComponent: %s\n")
		TEXT("  SkeletonPreset: %s\n\n")
		TEXT("  Skeleton: %s\n\n")
		TEXT("Manny wave preview plan\n")
		TEXT("  hand: %s\n")
		TEXT("  durationSeconds: %.2f\n")
		TEXT("  speed: %.2f\n")
		TEXT("  amplitude: %.2f\n")
		TEXT("  shoulderRaise: %.2f\n")
		TEXT("  elbowBend: %.2f\n")
		TEXT("  wristOscillation: %.2f\n\n")
		TEXT("Next adapter step\n")
		TEXT("  Map these parameters to CR_Mannequin_Procedural controls."),
		Actor ? *Actor->GetActorLabel() : TEXT("<invalid>"),
		MeshComponent ? *MeshComponent->GetName() : TEXT("<invalid>"),
		*Target.SkeletonPreset,
		*Target.SkeletonPath,
		*Gesture.Hand,
		Gesture.DurationSeconds,
		Gesture.Speed,
		Gesture.Amplitude,
		Gesture.ShoulderRaise,
		Gesture.ElbowBend,
		Gesture.WristOscillation);

	return true;
}
