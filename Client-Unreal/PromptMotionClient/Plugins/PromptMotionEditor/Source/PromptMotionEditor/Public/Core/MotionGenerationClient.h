#pragma once

#include "CoreMinimal.h"
#include "Data/PromptMotionTypes.h"

class FMotionGenerationClient
{
public:
	using FProceduralCallback = TFunction<void(bool bSuccess, const FProceduralGenerationResult& Result, const FString& ErrorMessage)>;
	using FEnrichedPromptCallback = TFunction<void(bool bSuccess, const FEnrichedPromptResult& Result, const FString& ErrorMessage)>;

	void GenerateProcedural(
		const FString& ServerBaseUrl,
		const FString& Prompt,
		const FString& SkeletonPreset,
		FProceduralCallback Callback) const;

	void GenerateEnrichedPrompt(
		const FString& ServerBaseUrl,
		const FString& Prompt,
		const FString& SkeletonPreset,
		FEnrichedPromptCallback Callback) const;

private:
	static FString BuildUrl(const FString& ServerBaseUrl, const FString& Route);
	static FString BuildPromptPayload(const FString& Prompt, const FString& SkeletonPreset);
	static bool ParseProceduralResponse(const FString& ResponseBody, FProceduralGenerationResult& OutResult, FString& OutError);
	static bool ParseEnrichedPromptResponse(const FString& ResponseBody, FEnrichedPromptResult& OutResult, FString& OutError);
};
