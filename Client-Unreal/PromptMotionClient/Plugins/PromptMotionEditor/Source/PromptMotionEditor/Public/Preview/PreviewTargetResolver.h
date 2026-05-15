#pragma once

#include "CoreMinimal.h"
#include "Preview/PreviewTarget.h"

class FPreviewTargetResolver
{
public:
	bool ResolveSelectedActor(const FString& RequestedSkeletonPreset, FPreviewTarget& OutTarget, FString& OutError) const;

private:
	static FString InferSkeletonPreset(const USkeletalMeshComponent& SkeletalMeshComponent);
};

