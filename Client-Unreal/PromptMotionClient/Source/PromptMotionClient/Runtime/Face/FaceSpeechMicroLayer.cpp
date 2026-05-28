#include "FaceSpeechMicroLayer.h"

namespace
{
constexpr float MinPoseIntervalSec = 0.65f;
constexpr float MaxPoseIntervalSec = 1.35f;
constexpr float MinIdlePoseIntervalSec = 1.8f;
constexpr float MaxIdlePoseIntervalSec = 3.4f;
constexpr float RiseInterpSpeed = 5.5f;
constexpr float FallInterpSpeed = 3.0f;
constexpr float MaxMicroOffset = 0.10f;
constexpr float IdleMicroScale = 0.45f;
constexpr float OffsetEpsilon = 0.002f;
}

void FFaceSpeechMicroLayer::Update(float DeltaTime, bool bSpeaking, bool bIdle, const FString& Emotion)
{
    if (DeltaTime <= 0.0f)
        return;

    if (!bInitialized)
    {
        ScheduleNextPose();
        bInitialized = true;
    }

    if (bSpeaking || bIdle)
    {
        TimeUntilNextPose -= DeltaTime;
        if (TimeUntilNextPose <= 0.0f)
        {
            PickPoseForEmotion(Emotion);
            if (bIdle)
            {
                for (auto& Pair : TargetOffsets)
                    Pair.Value *= IdleMicroScale;
                TimeUntilNextPose = FMath::FRandRange(MinIdlePoseIntervalSec, MaxIdlePoseIntervalSec);
            }
            else
            {
                ScheduleNextPose();
            }
        }
    }
    else
    {
        ClearTargets();
    }

    for (auto It = CurrentOffsets.CreateIterator(); It; ++It)
    {
        const float Current = It.Value();
        const float Target = TargetOffsets.FindRef(It.Key());
        const float Speed = Target > Current ? RiseInterpSpeed : FallInterpSpeed;
        const float Next = FMath::FInterpTo(Current, Target, DeltaTime, Speed);
        if (FMath::Abs(Next) <= OffsetEpsilon && FMath::Abs(Target) <= OffsetEpsilon)
            It.RemoveCurrent();
        else
            It.Value() = FMath::Clamp(Next, 0.0f, MaxMicroOffset);
    }

    for (const auto& Pair : TargetOffsets)
    {
        if (!CurrentOffsets.Contains(Pair.Key))
            CurrentOffsets.Add(Pair.Key, 0.0f);
    }
}

void FFaceSpeechMicroLayer::Reset()
{
    CurrentOffsets.Reset();
    TargetOffsets.Reset();
    TimeUntilNextPose = 0.0f;
    bInitialized = false;
}

bool FFaceSpeechMicroLayer::HasActiveOffsets() const
{
    if (!TargetOffsets.IsEmpty())
        return true;

    for (const auto& Pair : CurrentOffsets)
    {
        if (FMath::Abs(Pair.Value) > OffsetEpsilon)
            return true;
    }
    return false;
}

void FFaceSpeechMicroLayer::ScheduleNextPose()
{
    TimeUntilNextPose = FMath::FRandRange(MinPoseIntervalSec, MaxPoseIntervalSec);
}

void FFaceSpeechMicroLayer::PickPoseForEmotion(const FString& Emotion)
{
    ClearTargets();

    const FString Key = Emotion.ToLower();
    if (Key == TEXT("neutral"))
    {
        return;
    }
    if (Key == TEXT("thinking") || Key == TEXT("uncertain"))
    {
        AddSymmetricOffset(TEXT("Brow_Compress_L"), TEXT("Brow_Compress_R"), 0.025f, 0.055f);
        AddSymmetricOffset(TEXT("Eye_Squint_L"), TEXT("Eye_Squint_R"), 0.020f, 0.045f);
    }
    else if (Key == TEXT("curious") || Key == TEXT("surprised"))
    {
        AddSymmetricOffset(TEXT("Eye_Wide_L"), TEXT("Eye_Wide_R"), 0.030f, 0.070f);
        AddSymmetricOffset(TEXT("Brow_Raise_Outer_L"), TEXT("Brow_Raise_Outer_R"), 0.020f, 0.055f);
    }
    else if (Key == TEXT("concerned") || Key == TEXT("apologetic"))
    {
        AddSymmetricOffset(TEXT("Brow_Raise_Inner_L"), TEXT("Brow_Raise_Inner_R"), 0.025f, 0.060f);
        AddSymmetricOffset(TEXT("Brow_Compress_L"), TEXT("Brow_Compress_R"), 0.015f, 0.040f);
    }
    else if (Key == TEXT("listening"))
    {
        AddSymmetricOffset(TEXT("Eye_Squint_L"), TEXT("Eye_Squint_R"), 0.010f, 0.030f);
        AddSymmetricOffset(TEXT("Brow_Raise_Inner_L"), TEXT("Brow_Raise_Inner_R"), 0.010f, 0.030f);
    }
    else if (Key == TEXT("explaining"))
    {
        AddSymmetricOffset(TEXT("Eye_Wide_L"), TEXT("Eye_Wide_R"), 0.010f, 0.035f);
        AddSymmetricOffset(TEXT("Brow_Raise_Outer_L"), TEXT("Brow_Raise_Outer_R"), 0.010f, 0.035f);
    }
    else if (Key == TEXT("friendly") || Key == TEXT("happy"))
    {
        AddSymmetricOffset(TEXT("Cheek_Raise_L"), TEXT("Cheek_Raise_R"), 0.020f, 0.055f);
        AddSymmetricOffset(TEXT("Eye_Squint_L"), TEXT("Eye_Squint_R"), 0.015f, 0.040f);
    }
}

void FFaceSpeechMicroLayer::AddSymmetricOffset(const TCHAR* LeftMorph, const TCHAR* RightMorph, float MinValue, float MaxValue)
{
    const float Weight = FMath::FRandRange(MinValue, MaxValue);
    TargetOffsets.FindOrAdd(FName(LeftMorph)) = Weight;
    TargetOffsets.FindOrAdd(FName(RightMorph)) = Weight;
}

void FFaceSpeechMicroLayer::ClearTargets()
{
    TargetOffsets.Reset();
}
