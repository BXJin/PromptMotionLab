#pragma once

#include "CoreMinimal.h"

class USkeletalMeshComponent;

/**
 * LipSync 레이어 — Azure TTS viseme 이벤트 → CC4 V_* morph 적용.
 *
 * [STUB] 현재 미구현. Azure TTS SDK 연동 시 이 클래스를 채운다.
 *
 * 도메인: FaceMorphDomains::LipSync() 목록만 제어.
 *         Expression/Idle 도메인은 절대 건드리지 않음.
 *
 * ── Azure TTS Viseme ID → CC4 morph 매핑 (근사값) ──────────────────
 *
 *  ID | 음소             | CC4 morph
 * ----|-----------------|-------------------
 *   0 | silence         | (reset all LipSync)
 *   1 | æ ə ʌ           | V_Open
 *   2 | ɑ               | V_Open
 *   3 | ɔ               | V_Lip_Open
 *   4 | ɛ ʊ             | V_Open
 *   5 | ɝ               | V_Tight
 *   6 | j i ɪ           | V_Wide
 *   7 | w u             | V_Bilabial
 *   8 | o               | V_Lip_Open
 *   9 | aʊ              | V_Open
 *  10 | ɔɪ              | V_Lip_Open
 *  11 | aɪ              | V_Open
 *  12 | h               | V_Open
 *  13 | ɹ               | V_Tight
 *  14 | l               | V_Dental_Lip
 *  15 | s z             | V_Tight
 *  16 | ʃ tʃ dʒ ʒ       | V_Bilabial
 *  17 | ð               | V_Dental_Lip
 *  18 | f v             | V_Dental_Lip
 *  19 | d t n θ         | V_Affricate
 *  20 | k g ŋ           | V_Open
 *  21 | p b m           | V_Bilabial
 *
 * ────────────────────────────────────────────────────────────────────
 *
 * 통합 체크리스트 (구현 시점):
 *   [ ] Azure TTS SDK SpeechSynthesizer 연동
 *   [ ] OnVisemeReceived 콜백에서 ApplyViseme() 호출
 *   [ ] 발화 시작 시 Expression Layer의 Jaw_Open 개입 없는지 확인
 *   [ ] 발화 종료 시 ResetLipSync() 호출
 *   [ ] PromptMotionRuntimeComponent에 FFaceLipSyncLayer 멤버 추가
 */
class FFaceLipSyncLayer
{
public:
    /**
     * Azure TTS viseme 이벤트 수신 시 호출.
     * @param VisemeId  Azure TTS viseme ID (0~21)
     * @param Weight    입모양 강도 (0.0~1.0). TTS amplitude 또는 고정값 사용.
     * @param Mesh      대상 SkeletalMeshComponent
     */
    void ApplyViseme(int32 VisemeId, float Weight, USkeletalMeshComponent* Mesh);

    /**
     * 발화 종료 또는 취소 시 LipSync 도메인 전체 초기화.
     * Expression/Idle 도메인은 건드리지 않음.
     */
    void ResetLipSync(USkeletalMeshComponent* Mesh);
};
