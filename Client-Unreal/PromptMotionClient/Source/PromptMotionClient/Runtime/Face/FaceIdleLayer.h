#pragma once

#include "CoreMinimal.h"

class USkeletalMeshComponent;

class FFaceIdleLayer
{
public:
    void Update(float DeltaTime, USkeletalMeshComponent* Mesh, bool bSpeaking);
    void Reset(USkeletalMeshComponent* Mesh);

private:
    enum class EBlinkState : uint8
    {
        Waiting,
        Closing,
        Holding,
        Opening,
    };

    EBlinkState BlinkState = EBlinkState::Waiting;
    float TimeUntilNextBlink = 0.0f;
    float BlinkElapsed = 0.0f;
    float ActiveBlinkIntensity = 1.0f;
    bool bInitialized = false;

    void ScheduleNextBlink(bool bSpeaking);
    void StartBlink(bool bSpeaking);
    void ApplyBlink(USkeletalMeshComponent* Mesh, float Weight) const;
};
