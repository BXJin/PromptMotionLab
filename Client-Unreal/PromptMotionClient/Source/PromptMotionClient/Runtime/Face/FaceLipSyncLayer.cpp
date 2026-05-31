#include "FaceLipSyncLayer.h"

#include "Components/SkeletalMeshComponent.h"
#include "FaceMorphDomains.h"
#include "PromptMotionLog.h"

namespace
{
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
    UE_LOG(LogPromptMotion, Log, TEXT("[TTS] LipSync CSV not found — using embedded default_girl viseme mappings: character=%s path=%s"),
        *ActiveCharacterId, *FPromptMotionFaceConfig::GetLipSyncVisemeCsvPath(ActiveCharacterId));
}

void FFaceLipSyncLayer::BuildFallbackMappings()
{
    VisemeMappings.Reset();

    // Embedded production data — mirrors lipsync_visemes_default_girl.csv exactly.
    // CSV is still loaded first (see ReloadMappings); this runs only when the file is unavailable (e.g. Android PAK).
    // To regenerate: update both CSV and this table together.
    struct FEntry { int32 Id; const TCHAR* Morph; float W; float FI; float FO; };
    static const FEntry Entries[] = {
        // 0 — silence / reset
        { 0, TEXT("V_Lip_Open"),         0.00f, 0.060f, 0.100f },
        { 0, TEXT("V_Open"),             0.00f, 0.060f, 0.100f },
        { 0, TEXT("V_Wide"),             0.00f, 0.060f, 0.100f },
        { 0, TEXT("V_Tight"),            0.00f, 0.060f, 0.100f },
        { 0, TEXT("V_Tight_O"),          0.00f, 0.060f, 0.100f },
        // 1 — p,b,m
        { 1, TEXT("Mouth_Close"),       -0.07f, 0.055f, 0.095f },
        { 1, TEXT("V_Lip_Open"),         0.21f, 0.055f, 0.095f },
        { 1, TEXT("V_Open"),             0.07f, 0.060f, 0.100f },
        // 2 — f,v (dental)
        { 2, TEXT("Mouth_Close"),       -0.11f, 0.055f, 0.100f },
        { 2, TEXT("V_Lip_Open"),         0.32f, 0.055f, 0.100f },
        { 2, TEXT("V_Open"),             0.10f, 0.060f, 0.105f },
        { 2, TEXT("Mouth_Shrug_Upper"),  0.06f, 0.060f, 0.110f },
        // 3 — th
        { 3, TEXT("Mouth_Close"),       -0.07f, 0.055f, 0.095f },
        { 3, TEXT("V_Tight_O"),          0.44f, 0.055f, 0.095f },
        { 3, TEXT("V_Tight"),            0.17f, 0.060f, 0.100f },
        // 4 — d,t,n
        { 4, TEXT("Mouth_Close"),       -0.10f, 0.055f, 0.095f },
        { 4, TEXT("V_Lip_Open"),         0.24f, 0.055f, 0.095f },
        { 4, TEXT("V_Wide"),             0.14f, 0.060f, 0.100f },
        // 5 — k,g
        { 5, TEXT("V_Tight"),            0.36f, 0.055f, 0.095f },
        { 5, TEXT("V_Tight_O"),          0.14f, 0.060f, 0.100f },
        // 6 — ch,j,sh
        { 6, TEXT("V_Wide"),             0.26f, 0.055f, 0.095f },
        { 6, TEXT("V_Lip_Open"),         0.14f, 0.060f, 0.100f },
        // 7 — s,z
        { 7, TEXT("V_Tight"),            0.52f, 0.050f, 0.090f },
        { 7, TEXT("V_Tight_O"),          0.34f, 0.050f, 0.090f },
        // 8 — n (nasal)
        { 8, TEXT("V_Tight_O"),          0.52f, 0.050f, 0.090f },
        { 8, TEXT("V_Tight"),            0.24f, 0.055f, 0.095f },
        // 9 — uh/ow
        { 9, TEXT("Mouth_Close"),       -0.18f, 0.055f, 0.100f },
        { 9, TEXT("V_Lip_Open"),         0.25f, 0.055f, 0.100f },
        { 9, TEXT("V_Tight_O"),          0.25f, 0.060f, 0.105f },
        { 9, TEXT("Mouth_Shrug_Upper"),  0.05f, 0.060f, 0.110f },
        // 10 — oo
        {10, TEXT("V_Tight_O"),          0.36f, 0.055f, 0.100f },
        {10, TEXT("V_Wide"),             0.20f, 0.060f, 0.105f },
        {10, TEXT("V_Lip_Open"),         0.10f, 0.060f, 0.105f },
        // 11 — oh
        {11, TEXT("Mouth_Close"),       -0.18f, 0.055f, 0.100f },
        {11, TEXT("V_Lip_Open"),         0.27f, 0.055f, 0.100f },
        {11, TEXT("V_Wide"),             0.19f, 0.060f, 0.105f },
        {11, TEXT("Mouth_Shrug_Upper"),  0.05f, 0.060f, 0.110f },
        // 12 — ae
        {12, TEXT("Mouth_Close"),       -0.08f, 0.055f, 0.095f },
        {12, TEXT("V_Lip_Open"),         0.19f, 0.055f, 0.095f },
        {12, TEXT("V_Open"),             0.07f, 0.060f, 0.100f },
        // 13 — ih
        {13, TEXT("V_Tight"),            0.28f, 0.055f, 0.095f },
        {13, TEXT("V_Tight_O"),          0.12f, 0.060f, 0.100f },
        // 14 — l
        {14, TEXT("V_Tongue_Raise"),     0.45f, 0.055f, 0.095f },
        {14, TEXT("V_Lip_Open"),         0.12f, 0.060f, 0.100f },
        // 15 — r
        {15, TEXT("V_Tight"),            0.24f, 0.055f, 0.095f },
        {15, TEXT("V_Wide"),             0.10f, 0.060f, 0.100f },
        // 16 — y
        {16, TEXT("V_Affricate"),        0.36f, 0.050f, 0.090f },
        {16, TEXT("V_Tight_O"),          0.16f, 0.055f, 0.095f },
        // 17 — th (voiced)
        {17, TEXT("V_Tongue_Out"),       0.45f, 0.055f, 0.095f },
        {17, TEXT("V_Lip_Open"),         0.09f, 0.060f, 0.100f },
        // 18 — f,v (labiodental)
        {18, TEXT("V_Dental_Lip"),       0.34f, 0.050f, 0.090f },
        // 19 — dh
        {19, TEXT("V_Lip_Open"),         0.14f, 0.055f, 0.095f },
        {19, TEXT("V_Affricate"),        0.18f, 0.055f, 0.095f },
        // 20 — uh (schwa)
        {20, TEXT("Mouth_Close"),       -0.08f, 0.055f, 0.095f },
        {20, TEXT("V_Open"),             0.08f, 0.060f, 0.100f },
        {20, TEXT("V_Lip_Open"),         0.12f, 0.060f, 0.100f },
        // 21 — b,p (plosive burst)
        {21, TEXT("V_Explosive"),        0.10f, 0.045f, 0.085f },
        {21, TEXT("Mouth_Shrug_Lower"), -0.10f, 0.050f, 0.080f },
    };

    for (const FEntry& E : Entries)
    {
        FPromptMotionMorphWeight Entry;
        Entry.MorphName   = FName(E.Morph);
        Entry.Weight      = E.W;
        Entry.FadeInSec   = E.FI;
        Entry.FadeOutSec  = E.FO;
        VisemeMappings.FindOrAdd(E.Id).Add(Entry);
    }
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
