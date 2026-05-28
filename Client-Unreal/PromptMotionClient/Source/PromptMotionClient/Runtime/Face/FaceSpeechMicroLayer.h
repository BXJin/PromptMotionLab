#pragma once

#include "CoreMinimal.h"

class FFaceSpeechMicroLayer
{
public:
    void Update(float DeltaTime, bool bSpeaking, bool bIdle, const FString& Emotion);
    void Reset();

    const TMap<FName, float>& GetOffsets() const { return CurrentOffsets; }
    bool HasActiveOffsets() const;

private:
    TMap<FName, float> CurrentOffsets;
    TMap<FName, float> TargetOffsets;
    float TimeUntilNextPose = 0.0f;
    bool bInitialized = false;

    void ScheduleNextPose();
    void PickPoseForEmotion(const FString& Emotion);
    void AddSymmetricOffset(const TCHAR* LeftMorph, const TCHAR* RightMorph, float MinValue, float MaxValue);
    void ClearTargets();
};
