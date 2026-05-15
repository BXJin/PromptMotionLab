#pragma once

#include "CoreMinimal.h"

class AActor;
class USkeletalMeshComponent;

struct FPreviewTarget
{
	TWeakObjectPtr<AActor> Actor;
	TWeakObjectPtr<USkeletalMeshComponent> SkeletalMeshComponent;
	FString SkeletonPreset;
	FString SkeletonPath;
	FString DisplayName;

	bool IsValid() const
	{
		return Actor.IsValid() && SkeletalMeshComponent.IsValid();
	}
};
