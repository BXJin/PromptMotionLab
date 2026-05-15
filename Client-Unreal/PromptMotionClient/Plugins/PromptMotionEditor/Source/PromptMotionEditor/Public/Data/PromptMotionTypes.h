#pragma once

#include "CoreMinimal.h"

struct FMotionSpec
{
	FString Gesture;
	FString Hand;
	FString Emotion;
	FString Style;
	FString BodyScope;
	FString SkeletonPreset;
	double DurationSeconds = 0.0;
	double Speed = 0.0;
	double Amplitude = 0.0;
	bool bFeetPlanted = true;
	bool bRootMotion = false;
};

struct FProceduralGesture
{
	FString Gesture;
	FString Hand;
	FString SkeletonPreset;
	double DurationSeconds = 0.0;
	double Speed = 0.0;
	double Amplitude = 0.0;
	double ShoulderRaise = 0.0;
	double ElbowBend = 0.0;
	double WristOscillation = 0.0;
	double BodyLean = 0.0;
	double HeadNod = 0.0;
	bool bFeetPlanted = true;
	bool bRootMotion = false;
};

struct FPromptExport
{
	FString ExportId;
	FString OriginalPrompt;
	FString EnrichedPrompt;
	FString CreatedAtUtc;
	FString TargetProviderHint;
};

struct FProceduralGenerationResult
{
	FMotionSpec MotionSpec;
	FProceduralGesture ProceduralGesture;
	FString RawJson;
};

struct FEnrichedPromptResult
{
	FPromptExport Export;
	FString RawJson;
};
