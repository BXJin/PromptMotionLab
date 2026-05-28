#pragma once

#include "CoreMinimal.h"
#include "PromptMotionFaceConfig.h"

class USkeletalMeshComponent;

class FFaceLipSyncLayer
{
public:
    void LoadMappingsForCharacter(const FString& CharacterId);
    void ReloadMappings();

    void ApplyViseme(int32 VisemeId, float Weight, USkeletalMeshComponent* Mesh);

    /** 현재 매핑에서 visemeId + morph의 저장된 weight 반환. 없으면 0.0f. */
    float QueryVisemeWeight(int32 VisemeId, FName MorphName) const;
    void Update(float DeltaTime, USkeletalMeshComponent* Mesh);
    void ResetLipSync(USkeletalMeshComponent* Mesh);

private:
    FString ActiveCharacterId = TEXT("default_girl");
    FPromptMotionFaceConfig::FLipSyncVisemeMap VisemeMappings;
    TMap<FName, float> CurrentWeights;
    TMap<FName, float> TargetWeights;
    TMap<FName, float> TargetFadeSeconds;

    void BuildFallbackMappings();
};
