#include "Preview/PreviewTargetResolver.h"

#include "Animation/Skeleton.h"
#include "Components/SkeletalMeshComponent.h"
#include "Editor.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/Actor.h"
#include "Selection.h"

bool FPreviewTargetResolver::ResolveSelectedActor(
	const FString& RequestedSkeletonPreset,
	FPreviewTarget& OutTarget,
	FString& OutError) const
{
	if (!GEditor)
	{
		OutError = TEXT("GEditor is not available.");
		return false;
	}

	USelection* SelectedActors = GEditor->GetSelectedActors();
	if (!SelectedActors || SelectedActors->Num() == 0)
	{
		OutError = TEXT("Select an Actor with a SkeletalMeshComponent in the level.");
		return false;
	}

	AActor* SelectedActor = Cast<AActor>(SelectedActors->GetSelectedObject(0));
	if (!SelectedActor)
	{
		OutError = TEXT("The selected object is not an Actor.");
		return false;
	}

	USkeletalMeshComponent* SkeletalMeshComponent = SelectedActor->FindComponentByClass<USkeletalMeshComponent>();
	if (!SkeletalMeshComponent)
	{
		OutError = FString::Printf(TEXT("Actor '%s' has no SkeletalMeshComponent."), *SelectedActor->GetActorLabel());
		return false;
	}

	if (!SkeletalMeshComponent->GetSkeletalMeshAsset())
	{
		OutError = FString::Printf(TEXT("Actor '%s' has no SkeletalMesh asset."), *SelectedActor->GetActorLabel());
		return false;
	}

	const FString InferredPreset = InferSkeletonPreset(*SkeletalMeshComponent);
	if (!RequestedSkeletonPreset.Equals(InferredPreset, ESearchCase::IgnoreCase))
	{
		const USkeleton* Skeleton = SkeletalMeshComponent->GetSkeletalMeshAsset()->GetSkeleton();
		const FString SkeletonPath = Skeleton ? Skeleton->GetOutermost()->GetName() : TEXT("<none>");
		OutError = FString::Printf(
			TEXT("Selected Actor preset is '%s', but panel requests '%s'. Skeleton: %s"),
			*InferredPreset,
			*RequestedSkeletonPreset,
			*SkeletonPath);
		return false;
	}

	const USkeleton* Skeleton = SkeletalMeshComponent->GetSkeletalMeshAsset()->GetSkeleton();
	OutTarget.Actor = SelectedActor;
	OutTarget.SkeletalMeshComponent = SkeletalMeshComponent;
	OutTarget.SkeletonPreset = InferredPreset;
	OutTarget.SkeletonPath = Skeleton ? Skeleton->GetOutermost()->GetName() : TEXT("<none>");
	OutTarget.DisplayName = FString::Printf(
		TEXT("%s / %s"),
		*SelectedActor->GetActorLabel(),
		*SkeletalMeshComponent->GetSkeletalMeshAsset()->GetName());
	return true;
}

FString FPreviewTargetResolver::InferSkeletonPreset(const USkeletalMeshComponent& SkeletalMeshComponent)
{
	const USkeletalMesh* SkeletalMesh = SkeletalMeshComponent.GetSkeletalMeshAsset();
	if (!SkeletalMesh || !SkeletalMesh->GetSkeleton())
	{
		return TEXT("unknown");
	}

	const FString SkeletonPackagePath = SkeletalMesh->GetSkeleton()->GetOutermost()->GetName();
	if (SkeletonPackagePath.Equals(TEXT("/Game/Characters/Mannequins/Meshes/SK_Mannequin"), ESearchCase::IgnoreCase))
	{
		return TEXT("ue5_manny");
	}

	if (SkeletonPackagePath.Equals(TEXT("/Game/Characters/Mannequin_UE4/Meshes/SK_Mannequin_Skeleton"), ESearchCase::IgnoreCase))
	{
		return TEXT("ue4_mannequin");
	}

	return TEXT("unknown");
}
