#include "FaceMorphDomains.h"

const TSet<FName>& FFaceMorphDomains::LipSync()
{
    // CC4 V_* viseme morphs + Jaw_Open + Mouth_Close
    // Azure TTS viseme 이벤트가 이 morphs를 프레임 단위로 제어한다.
    // Expression preset에 이 이름이 들어가면 ValidateNoConflict()가 잡아낸다.
    static const TSet<FName> Domain = []()
    {
        TSet<FName> D;
        D.Add(TEXT("Jaw_Open"));
        D.Add(TEXT("Mouth_Close"));
        D.Add(TEXT("V_Open"));
        D.Add(TEXT("V_Wide"));
        D.Add(TEXT("V_Tight"));
        D.Add(TEXT("V_Dental_Lip"));
        D.Add(TEXT("V_Affricate"));
        D.Add(TEXT("V_Bilabial"));
        D.Add(TEXT("V_Lip_Open"));
        return D;
    }();
    return Domain;
}

const TSet<FName>& FFaceMorphDomains::Idle()
{
    // BlinkController 구현 전까지 비어있음.
    // Eye_Blink_L/R은 BlinkController 없이도 Expression preset에서 쓸 수 있으므로
    // 격리하지 않는다. BlinkController 추가 시 이 도메인에 등록할 것.
    static const TSet<FName> Domain;
    return Domain;
}

const TSet<FName>& FFaceMorphDomains::Expression()
{
    // FacePresetResolver preset에 등장하는 morph 목록.
    // LipSync/Idle 도메인과 교차 없음 — ValidateNoConflict()로 보장.
    static const TSet<FName> Domain = []()
    {
        TSet<FName> D;
        D.Add(TEXT("Brow_Raise_Inner_L")); D.Add(TEXT("Brow_Raise_Inner_R"));
        D.Add(TEXT("Brow_Raise_Outer_L")); D.Add(TEXT("Brow_Raise_Outer_R"));
        D.Add(TEXT("Brow_Compress_L"));    D.Add(TEXT("Brow_Compress_R"));
        D.Add(TEXT("Brow_Drop_L"));        D.Add(TEXT("Brow_Drop_R"));
        D.Add(TEXT("Cheek_Raise_L"));      D.Add(TEXT("Cheek_Raise_R"));
        D.Add(TEXT("Cheek_Puff_L"));       D.Add(TEXT("Cheek_Puff_R"));
        D.Add(TEXT("Cheek_Suck_L"));       D.Add(TEXT("Cheek_Suck_R"));
        D.Add(TEXT("Eye_Squint_L"));       D.Add(TEXT("Eye_Squint_R"));
        D.Add(TEXT("Eye_Wide_L"));         D.Add(TEXT("Eye_Wide_R"));
        D.Add(TEXT("Mouth_Smile_L"));      D.Add(TEXT("Mouth_Smile_R"));
        D.Add(TEXT("Mouth_Frown_L"));      D.Add(TEXT("Mouth_Frown_R"));
        D.Add(TEXT("Mouth_Tighten_L"));    D.Add(TEXT("Mouth_Tighten_R"));
        D.Add(TEXT("Mouth_Press_L"));      D.Add(TEXT("Mouth_Press_R"));
        D.Add(TEXT("Mouth_Pucker_L"));     D.Add(TEXT("Mouth_Pucker_R"));
        D.Add(TEXT("Nose_Crease_L"));      D.Add(TEXT("Nose_Crease_R"));
        return D;
    }();
    return Domain;
}

void FFaceMorphDomains::ValidateNoConflict(const TMap<FName, float>& PresetMorphs, const FString& PresetName)
{
#if !UE_BUILD_SHIPPING
    for (const auto& Pair : PresetMorphs)
    {
        ensureMsgf(
            !LipSync().Contains(Pair.Key),
            TEXT("[FaceMorphDomains] Expression preset '%s'에 LipSync 도메인 morph '%s'가 포함됨. "
                 "TTS 립싱크와 충돌 발생. 해당 morph를 preset에서 제거할 것."),
            *PresetName, *Pair.Key.ToString()
        );

        ensureMsgf(
            !Idle().Contains(Pair.Key),
            TEXT("[FaceMorphDomains] Expression preset '%s'에 Idle 도메인 morph '%s'가 포함됨. "
                 "눈 깜빡임과 충돌 발생. 해당 morph를 preset에서 제거할 것."),
            *PresetName, *Pair.Key.ToString()
        );
    }
#endif
}
