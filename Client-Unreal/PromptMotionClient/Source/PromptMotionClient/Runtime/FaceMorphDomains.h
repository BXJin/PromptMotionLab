#pragma once

#include "CoreMinimal.h"

/**
 * Morph Target 레이어 도메인 경계 정의.
 *
 * 규칙: 각 레이어는 자신의 도메인 morph만 SetMorphTarget으로 제어한다.
 * 도메인 교차 금지. 새 레이어 추가 시 반드시 이 파일에 먼저 등록할 것.
 *
 *  Layer       | Priority | Owner Class          | Trigger
 * -------------|----------|----------------------|---------------------------
 *  Idle        |    0     | (미구현) BlinkCtrl   | 타이머 자동
 *  Expression  |    1     | FacePresetResolver   | Behavior JSON 응답
 *  LipSync     |    2     | FaceLipSyncLayer     | TTS viseme 이벤트
 *
 * ValidateNoConflict() — Development/Debug 빌드에서만 동작.
 * Expression preset에 LipSync/Idle 도메인 morph가 포함되면 즉시 ensure 발생.
 */
struct FFaceMorphDomains
{
    /** Expression preset 독점 morphs (FacePresetResolver가 제어) */
    static const TSet<FName>& Expression();

    /** LipSync 독점 morphs — TTS viseme 전용. Expression/Idle은 절대 포함 금지. */
    static const TSet<FName>& LipSync();

    /** Idle/Blink 도메인 — BlinkController 구현 전까지 빈 집합. */
    static const TSet<FName>& Idle();

    /**
     * preset morph 집합이 LipSync/Idle 도메인과 겹치지 않는지 검증.
     * 충돌 시 ensure 발생 + 로그 출력.
     * UE_BUILD_SHIPPING에서는 컴파일 아웃.
     */
    static void ValidateNoConflict(const TMap<FName, float>& PresetMorphs, const FString& PresetName);
};
