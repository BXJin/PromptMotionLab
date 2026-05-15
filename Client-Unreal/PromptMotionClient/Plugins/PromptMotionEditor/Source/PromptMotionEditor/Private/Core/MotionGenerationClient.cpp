#include "Core/MotionGenerationClient.h"

#include "Dom/JsonObject.h"
#include "HttpModule.h"
#include "Interfaces/IHttpResponse.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
	TSharedPtr<FJsonObject> DeserializeJsonObject(const FString& Body, FString& OutError)
	{
		TSharedPtr<FJsonObject> JsonObject;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Body);
		if (!FJsonSerializer::Deserialize(Reader, JsonObject) || !JsonObject.IsValid())
		{
			OutError = TEXT("Failed to parse JSON response.");
			return nullptr;
		}

		return JsonObject;
	}

	TSharedPtr<FJsonObject> GetObjectField(const TSharedPtr<FJsonObject>& Object, const FString& FieldName)
	{
		if (!Object.IsValid())
		{
			return nullptr;
		}

		const TSharedPtr<FJsonObject>* Nested = nullptr;
		return Object->TryGetObjectField(FieldName, Nested) ? *Nested : nullptr;
	}

	FString GetString(const TSharedPtr<FJsonObject>& Object, const FString& FieldName, const FString& DefaultValue = TEXT(""))
	{
		FString Value;
		return Object.IsValid() && Object->TryGetStringField(FieldName, Value) ? Value : DefaultValue;
	}

	double GetNumber(const TSharedPtr<FJsonObject>& Object, const FString& FieldName, double DefaultValue = 0.0)
	{
		double Value = 0.0;
		return Object.IsValid() && Object->TryGetNumberField(FieldName, Value) ? Value : DefaultValue;
	}

	bool GetBool(const TSharedPtr<FJsonObject>& Object, const FString& FieldName, bool bDefaultValue = false)
	{
		bool bValue = false;
		return Object.IsValid() && Object->TryGetBoolField(FieldName, bValue) ? bValue : bDefaultValue;
	}

	FMotionSpec ParseMotionSpec(const TSharedPtr<FJsonObject>& Object)
	{
		FMotionSpec MotionSpec;
		MotionSpec.Gesture = GetString(Object, TEXT("gesture"));
		MotionSpec.Hand = GetString(Object, TEXT("hand"));
		MotionSpec.Emotion = GetString(Object, TEXT("emotion"));
		MotionSpec.Style = GetString(Object, TEXT("style"));
		MotionSpec.BodyScope = GetString(Object, TEXT("bodyScope"));
		MotionSpec.SkeletonPreset = GetString(Object, TEXT("skeletonPreset"), TEXT("ue5_manny"));
		MotionSpec.DurationSeconds = GetNumber(Object, TEXT("durationSeconds"));
		MotionSpec.Speed = GetNumber(Object, TEXT("speed"));
		MotionSpec.Amplitude = GetNumber(Object, TEXT("amplitude"));
		MotionSpec.bFeetPlanted = GetBool(Object, TEXT("feetPlanted"), true);
		MotionSpec.bRootMotion = GetBool(Object, TEXT("rootMotion"), false);
		return MotionSpec;
	}
}

void FMotionGenerationClient::GenerateProcedural(
	const FString& ServerBaseUrl,
	const FString& Prompt,
	const FString& SkeletonPreset,
	FProceduralCallback Callback) const
{
	const TSharedRef<IHttpRequest> Request = FHttpModule::Get().CreateRequest();
	Request->SetURL(BuildUrl(ServerBaseUrl, TEXT("/api/generate/procedural")));
	Request->SetVerb(TEXT("POST"));
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	Request->SetContentAsString(BuildPromptPayload(Prompt, SkeletonPreset));
	Request->OnProcessRequestComplete().BindLambda(
		[Callback = MoveTemp(Callback)](FHttpRequestPtr, FHttpResponsePtr Response, bool bConnectedSuccessfully)
		{
			FProceduralGenerationResult Result;
			if (!bConnectedSuccessfully || !Response.IsValid())
			{
				Callback(false, Result, TEXT("Server request failed."));
				return;
			}

			if (Response->GetResponseCode() < 200 || Response->GetResponseCode() >= 300)
			{
				Callback(false, Result, FString::Printf(TEXT("Server returned HTTP %d."), Response->GetResponseCode()));
				return;
			}

			FString Error;
			if (!ParseProceduralResponse(Response->GetContentAsString(), Result, Error))
			{
				Callback(false, Result, Error);
				return;
			}

			Callback(true, Result, TEXT(""));
		});
	Request->ProcessRequest();
}

void FMotionGenerationClient::GenerateEnrichedPrompt(
	const FString& ServerBaseUrl,
	const FString& Prompt,
	const FString& SkeletonPreset,
	FEnrichedPromptCallback Callback) const
{
	const TSharedRef<IHttpRequest> Request = FHttpModule::Get().CreateRequest();
	Request->SetURL(BuildUrl(ServerBaseUrl, TEXT("/api/generate/enriched-prompt")));
	Request->SetVerb(TEXT("POST"));
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	Request->SetContentAsString(BuildPromptPayload(Prompt, SkeletonPreset));
	Request->OnProcessRequestComplete().BindLambda(
		[Callback = MoveTemp(Callback)](FHttpRequestPtr, FHttpResponsePtr Response, bool bConnectedSuccessfully)
		{
			FEnrichedPromptResult Result;
			if (!bConnectedSuccessfully || !Response.IsValid())
			{
				Callback(false, Result, TEXT("Server request failed."));
				return;
			}

			if (Response->GetResponseCode() < 200 || Response->GetResponseCode() >= 300)
			{
				Callback(false, Result, FString::Printf(TEXT("Server returned HTTP %d."), Response->GetResponseCode()));
				return;
			}

			FString Error;
			if (!ParseEnrichedPromptResponse(Response->GetContentAsString(), Result, Error))
			{
				Callback(false, Result, Error);
				return;
			}

			Callback(true, Result, TEXT(""));
		});
	Request->ProcessRequest();
}

FString FMotionGenerationClient::BuildUrl(const FString& ServerBaseUrl, const FString& Route)
{
	FString Base = ServerBaseUrl;
	while (Base.EndsWith(TEXT("/")))
	{
		Base.LeftChopInline(1);
	}
	return Base + Route;
}

FString FMotionGenerationClient::BuildPromptPayload(const FString& Prompt, const FString& SkeletonPreset)
{
	const TSharedRef<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("prompt"), Prompt);
	Payload->SetStringField(TEXT("skeletonPreset"), SkeletonPreset);

	FString Body;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Body);
	FJsonSerializer::Serialize(Payload, Writer);
	return Body;
}

bool FMotionGenerationClient::ParseProceduralResponse(const FString& ResponseBody, FProceduralGenerationResult& OutResult, FString& OutError)
{
	OutResult.RawJson = ResponseBody;
	const TSharedPtr<FJsonObject> Root = DeserializeJsonObject(ResponseBody, OutError);
	if (!Root.IsValid())
	{
		return false;
	}

	const TSharedPtr<FJsonObject> MotionSpecObject = GetObjectField(Root, TEXT("motionSpec"));
	const TSharedPtr<FJsonObject> GestureObject = GetObjectField(Root, TEXT("proceduralGesture"));
	if (!MotionSpecObject.IsValid() || !GestureObject.IsValid())
	{
		OutError = TEXT("Response is missing motionSpec or proceduralGesture.");
		return false;
	}

	OutResult.MotionSpec = ParseMotionSpec(MotionSpecObject);
	OutResult.ProceduralGesture.Gesture = GetString(GestureObject, TEXT("gesture"));
	OutResult.ProceduralGesture.Hand = GetString(GestureObject, TEXT("hand"));
	OutResult.ProceduralGesture.SkeletonPreset = GetString(GestureObject, TEXT("skeletonPreset"), TEXT("ue5_manny"));
	OutResult.ProceduralGesture.DurationSeconds = GetNumber(GestureObject, TEXT("durationSeconds"));
	OutResult.ProceduralGesture.Speed = GetNumber(GestureObject, TEXT("speed"));
	OutResult.ProceduralGesture.Amplitude = GetNumber(GestureObject, TEXT("amplitude"));
	OutResult.ProceduralGesture.ShoulderRaise = GetNumber(GestureObject, TEXT("shoulderRaise"));
	OutResult.ProceduralGesture.ElbowBend = GetNumber(GestureObject, TEXT("elbowBend"));
	OutResult.ProceduralGesture.WristOscillation = GetNumber(GestureObject, TEXT("wristOscillation"));
	OutResult.ProceduralGesture.BodyLean = GetNumber(GestureObject, TEXT("bodyLean"));
	OutResult.ProceduralGesture.HeadNod = GetNumber(GestureObject, TEXT("headNod"));
	OutResult.ProceduralGesture.bFeetPlanted = GetBool(GestureObject, TEXT("feetPlanted"), true);
	OutResult.ProceduralGesture.bRootMotion = GetBool(GestureObject, TEXT("rootMotion"), false);
	return true;
}

bool FMotionGenerationClient::ParseEnrichedPromptResponse(const FString& ResponseBody, FEnrichedPromptResult& OutResult, FString& OutError)
{
	OutResult.RawJson = ResponseBody;
	const TSharedPtr<FJsonObject> Root = DeserializeJsonObject(ResponseBody, OutError);
	if (!Root.IsValid())
	{
		return false;
	}

	const TSharedPtr<FJsonObject> ExportObject = GetObjectField(Root, TEXT("export"));
	if (!ExportObject.IsValid())
	{
		OutError = TEXT("Response is missing export.");
		return false;
	}

	OutResult.Export.ExportId = GetString(ExportObject, TEXT("exportId"));
	OutResult.Export.OriginalPrompt = GetString(ExportObject, TEXT("originalPrompt"));
	OutResult.Export.EnrichedPrompt = GetString(ExportObject, TEXT("enrichedPrompt"));
	OutResult.Export.CreatedAtUtc = GetString(ExportObject, TEXT("createdAtUtc"));
	OutResult.Export.TargetProviderHint = GetString(ExportObject, TEXT("targetProviderHint"));
	return true;
}
