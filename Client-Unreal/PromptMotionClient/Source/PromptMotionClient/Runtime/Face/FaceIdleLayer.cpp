#include "FaceIdleLayer.h"

#include "Components/SkeletalMeshComponent.h"

namespace
{
constexpr float MinBlinkIntervalSec = 2.5f;
constexpr float MaxBlinkIntervalSec = 5.0f;
constexpr float SpeakingIntervalScale = 1.2f;
constexpr float BlinkCloseSec = 0.045f;
constexpr float BlinkHoldSec = 0.025f;
constexpr float BlinkOpenSec = 0.080f;
constexpr float IdleBlinkIntensity = 1.0f;
constexpr float SpeakingBlinkIntensity = 0.85f;

const FName BlinkLeftMorph(TEXT("Eye_Blink_L"));
const FName BlinkRightMorph(TEXT("Eye_Blink_R"));
}

void FFaceIdleLayer::Update(float DeltaTime, USkeletalMeshComponent* Mesh, bool bSpeaking)
{
    if (!Mesh || DeltaTime <= 0.0f)
        return;

    if (!bInitialized)
    {
        ScheduleNextBlink(bSpeaking);
        bInitialized = true;
    }

    switch (BlinkState)
    {
    case EBlinkState::Waiting:
        TimeUntilNextBlink -= DeltaTime;
        if (TimeUntilNextBlink <= 0.0f)
            StartBlink(bSpeaking);
        break;

    case EBlinkState::Closing:
    {
        BlinkElapsed += DeltaTime;
        const float Alpha = FMath::Clamp(BlinkElapsed / BlinkCloseSec, 0.0f, 1.0f);
        ApplyBlink(Mesh, FMath::Lerp(0.0f, ActiveBlinkIntensity, Alpha));
        if (Alpha >= 1.0f)
        {
            BlinkState = EBlinkState::Holding;
            BlinkElapsed = 0.0f;
        }
        break;
    }

    case EBlinkState::Holding:
        BlinkElapsed += DeltaTime;
        ApplyBlink(Mesh, ActiveBlinkIntensity);
        if (BlinkElapsed >= BlinkHoldSec)
        {
            BlinkState = EBlinkState::Opening;
            BlinkElapsed = 0.0f;
        }
        break;

    case EBlinkState::Opening:
    {
        BlinkElapsed += DeltaTime;
        const float Alpha = FMath::Clamp(BlinkElapsed / BlinkOpenSec, 0.0f, 1.0f);
        ApplyBlink(Mesh, FMath::Lerp(ActiveBlinkIntensity, 0.0f, Alpha));
        if (Alpha >= 1.0f)
        {
            BlinkState = EBlinkState::Waiting;
            BlinkElapsed = 0.0f;
            ApplyBlink(Mesh, 0.0f);
            ScheduleNextBlink(bSpeaking);
        }
        break;
    }
    }
}

void FFaceIdleLayer::Reset(USkeletalMeshComponent* Mesh)
{
    BlinkState = EBlinkState::Waiting;
    TimeUntilNextBlink = 0.0f;
    BlinkElapsed = 0.0f;
    ActiveBlinkIntensity = 1.0f;
    bInitialized = false;
    ApplyBlink(Mesh, 0.0f);
}

void FFaceIdleLayer::ScheduleNextBlink(bool bSpeaking)
{
    const float Scale = bSpeaking ? SpeakingIntervalScale : 1.0f;
    TimeUntilNextBlink = FMath::FRandRange(MinBlinkIntervalSec, MaxBlinkIntervalSec) * Scale;
}

void FFaceIdleLayer::StartBlink(bool bSpeaking)
{
    BlinkState = EBlinkState::Closing;
    BlinkElapsed = 0.0f;
    ActiveBlinkIntensity = bSpeaking ? SpeakingBlinkIntensity : IdleBlinkIntensity;
}

void FFaceIdleLayer::ApplyBlink(USkeletalMeshComponent* Mesh, float Weight) const
{
    if (!Mesh)
        return;

    const float Clamped = FMath::Clamp(Weight, 0.0f, 1.0f);
    Mesh->SetMorphTarget(BlinkLeftMorph, Clamped);
    Mesh->SetMorphTarget(BlinkRightMorph, Clamped);
}
