#include "FaceLipSyncLayer.h"

#include "Components/SkeletalMeshComponent.h"
#include "FaceMorphDomains.h"
#include "PromptMotionLog.h"

namespace
{
void AddMapping(FPromptMotionFaceConfig::FLipSyncVisemeMap& Map, int32 VisemeId, const TCHAR* MorphName, float Weight)
{
    FPromptMotionMorphWeight Entry;
    Entry.MorphName = FName(MorphName);
    Entry.Weight = FMath::Clamp(Weight, -1.0f, 1.0f);
    Map.FindOrAdd(VisemeId).Add(Entry);
}

float ClampLipSyncWeight(FName MorphName, float Weight)
{
    const float LowerBound = MorphName == TEXT("Mouth_Close") ? -0.35f : 0.0f;
    return FMath::Clamp(Weight, LowerBound, 0.75f);
}
}

void FFaceLipSyncLayer::LoadMappingsForCharacter(const FString& CharacterId)
{
    ActiveCharacterId = CharacterId.IsEmpty() ? TEXT("default_girl") : CharacterId;
    ReloadMappings();
}

void FFaceLipSyncLayer::ReloadMappings()
{
    VisemeMappings.Reset();
    if (FPromptMotionFaceConfig::LoadLipSyncVisemes(ActiveCharacterId, VisemeMappings))
    {
        UE_LOG(LogPromptMotion, Log, TEXT("[TTS] LipSync CSV loaded: character=%s visemes=%d path=%s"),
            *ActiveCharacterId, VisemeMappings.Num(), *FPromptMotionFaceConfig::GetLipSyncVisemeCsvPath(ActiveCharacterId));
        return;
    }

    BuildFallbackMappings();
    UE_LOG(LogPromptMotion, Warning, TEXT("[TTS] LipSync CSV missing or empty. Using fallback mappings: character=%s path=%s"),
        *ActiveCharacterId, *FPromptMotionFaceConfig::GetLipSyncVisemeCsvPath(ActiveCharacterId));
}

void FFaceLipSyncLayer::BuildFallbackMappings()
{
    VisemeMappings.Reset();

    AddMapping(VisemeMappings, 1, TEXT("V_Open"), 0.45f);
    AddMapping(VisemeMappings, 2, TEXT("Jaw_Open"), 0.45f); AddMapping(VisemeMappings, 2, TEXT("V_Open"), 0.55f);
    AddMapping(VisemeMappings, 3, TEXT("V_Lip_Open"), 0.55f); AddMapping(VisemeMappings, 3, TEXT("Jaw_Open"), 0.20f);
    AddMapping(VisemeMappings, 4, TEXT("V_Open"), 0.55f); AddMapping(VisemeMappings, 4, TEXT("Jaw_Open"), 0.35f);
    AddMapping(VisemeMappings, 5, TEXT("V_Tight"), 0.55f);
    AddMapping(VisemeMappings, 6, TEXT("V_Wide"), 0.65f); AddMapping(VisemeMappings, 6, TEXT("Jaw_Open"), 0.15f);
    AddMapping(VisemeMappings, 7, TEXT("V_Bilabial"), 0.45f); AddMapping(VisemeMappings, 7, TEXT("V_Tight_O"), 0.40f);
    AddMapping(VisemeMappings, 8, TEXT("V_Lip_Open"), 0.55f); AddMapping(VisemeMappings, 8, TEXT("V_Tight_O"), 0.35f);
    AddMapping(VisemeMappings, 9, TEXT("Jaw_Open"), 0.55f); AddMapping(VisemeMappings, 9, TEXT("V_Open"), 0.60f);
    AddMapping(VisemeMappings, 10, TEXT("V_Lip_Open"), 0.50f); AddMapping(VisemeMappings, 10, TEXT("V_Open"), 0.25f);
    AddMapping(VisemeMappings, 11, TEXT("Jaw_Open"), 0.60f); AddMapping(VisemeMappings, 11, TEXT("V_Open"), 0.65f);
    AddMapping(VisemeMappings, 12, TEXT("V_Open"), 0.35f); AddMapping(VisemeMappings, 12, TEXT("Jaw_Open"), 0.25f);
    AddMapping(VisemeMappings, 13, TEXT("V_Tight"), 0.45f); AddMapping(VisemeMappings, 13, TEXT("Mouth_Close"), 0.15f);
    AddMapping(VisemeMappings, 14, TEXT("V_Dental_Lip"), 0.55f); AddMapping(VisemeMappings, 14, TEXT("V_Tongue_Raise"), 0.30f);
    AddMapping(VisemeMappings, 15, TEXT("V_Tight"), 0.60f); AddMapping(VisemeMappings, 15, TEXT("V_Wide"), 0.25f);
    AddMapping(VisemeMappings, 16, TEXT("V_Affricate"), 0.45f); AddMapping(VisemeMappings, 16, TEXT("V_Bilabial"), 0.25f);
    AddMapping(VisemeMappings, 17, TEXT("V_Dental_Lip"), 0.45f); AddMapping(VisemeMappings, 17, TEXT("V_Tight"), 0.25f);
    AddMapping(VisemeMappings, 18, TEXT("V_Dental_Lip"), 0.65f); AddMapping(VisemeMappings, 18, TEXT("Mouth_Close"), 0.15f);
    AddMapping(VisemeMappings, 19, TEXT("V_Affricate"), 0.60f); AddMapping(VisemeMappings, 19, TEXT("V_Tongue_Raise"), 0.25f);
    AddMapping(VisemeMappings, 20, TEXT("V_Open"), 0.45f); AddMapping(VisemeMappings, 20, TEXT("Jaw_Open"), 0.25f);
    AddMapping(VisemeMappings, 21, TEXT("V_Bilabial"), 0.65f); AddMapping(VisemeMappings, 21, TEXT("Mouth_Close"), 0.30f);
}

float FFaceLipSyncLayer::QueryVisemeWeight(int32 VisemeId, FName MorphName) const
{
    const TArray<FPromptMotionMorphWeight>* Mappings = VisemeMappings.Find(VisemeId);
    if (!Mappings)
        return 0.0f;

    for (const FPromptMotionMorphWeight& M : *Mappings)
    {
        if (M.MorphName == MorphName)
            return M.Weight;
    }
    return 0.0f;
}

void FFaceLipSyncLayer::ApplyViseme(int32 VisemeId, float Weight, USkeletalMeshComponent* Mesh)
{
    if (!Mesh)
        return;

    if (VisemeId < 0 || VisemeId > 21)
    {
        ResetLipSync(Mesh);
        return;
    }

    if (VisemeMappings.IsEmpty())
        ReloadMappings();

    const TArray<FPromptMotionMorphWeight>* Mappings = VisemeMappings.Find(VisemeId);
    if (!Mappings || Mappings->IsEmpty())
    {
        ResetLipSync(Mesh);
        return;
    }

    const TSet<FName>& LipDomain = FFaceMorphDomains::LipSync();
    for (const FName& Morph : LipDomain)
    {
        TargetWeights.FindOrAdd(Morph) = 0.0f;
        CurrentWeights.FindOrAdd(Morph, 0.0f);
        TargetFadeSeconds.FindOrAdd(Morph) = 0.08f;
    }

    for (const FPromptMotionMorphWeight& Mapping : *Mappings)
    {
        if (!LipDomain.Contains(Mapping.MorphName))
        {
            UE_LOG(LogPromptMotion, Verbose, TEXT("[TTS] LipSync morph skipped outside domain: %s"),
                *Mapping.MorphName.ToString());
            continue;
        }

        TargetWeights.FindOrAdd(Mapping.MorphName) =
            ClampLipSyncWeight(Mapping.MorphName, Mapping.Weight * FMath::Clamp(Weight, 0.0f, 1.0f));
        TargetFadeSeconds.FindOrAdd(Mapping.MorphName) = Mapping.FadeInSec;
    }
}

void FFaceLipSyncLayer::Update(float DeltaTime, USkeletalMeshComponent* Mesh)
{
    if (!Mesh)
        return;

    for (const FName& Morph : FFaceMorphDomains::LipSync())
    {
        const float Current = CurrentWeights.FindRef(Morph);
        const float Target = TargetWeights.FindRef(Morph);
        const float FadeSec = TargetFadeSeconds.FindRef(Morph);
        const float InterpSpeed = FadeSec <= SMALL_NUMBER ? 1000.0f : 4.0f / FadeSec;
        const float Next = FMath::FInterpTo(Current, Target, DeltaTime, InterpSpeed);
        CurrentWeights.FindOrAdd(Morph) = Next;
        Mesh->SetMorphTarget(Morph, Next);
    }
}

void FFaceLipSyncLayer::ResetLipSync(USkeletalMeshComponent* Mesh)
{
    if (!Mesh)
        return;

    for (const FName& Morph : FFaceMorphDomains::LipSync())
    {
        Mesh->SetMorphTarget(Morph, 0.0f);
    }
    CurrentWeights.Empty();
    TargetWeights.Empty();
    TargetFadeSeconds.Empty();
}
