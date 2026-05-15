from fastapi import APIRouter, Depends, HTTPException

from app.contracts import (
    AnalyzeIntentRequest,
    AnalyzeIntentResponse,
    EnrichedPromptRequest,
    EnrichedPromptResponse,
    HealthResponse,
    ProceduralGenerationRequest,
    ProceduralGenerationResponse,
    RuntimeRespondRequest,
    RuntimeRespondResponse,
)
from app.dependencies import get_motion_generation_service, get_runtime_character_service
from app.services import MotionGenerationService, RuntimeCharacterService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.post("/api/analyze-intent", response_model=AnalyzeIntentResponse)
async def analyze_intent(
    request: AnalyzeIntentRequest,
    service: MotionGenerationService = Depends(get_motion_generation_service),
) -> AnalyzeIntentResponse:
    motion_spec = await service.analyze_intent(request.prompt, request.skeleton_preset)
    return AnalyzeIntentResponse(motionSpec=motion_spec)


@router.post("/api/generate/procedural", response_model=ProceduralGenerationResponse)
async def generate_procedural(
    request: ProceduralGenerationRequest,
    service: MotionGenerationService = Depends(get_motion_generation_service),
) -> ProceduralGenerationResponse:
    motion_spec, gesture = await service.generate_procedural(
        request.prompt,
        request.skeleton_preset,
    )
    return ProceduralGenerationResponse(motionSpec=motion_spec, proceduralGesture=gesture)


@router.post("/api/generate/enriched-prompt", response_model=EnrichedPromptResponse)
async def generate_enriched_prompt(
    request: EnrichedPromptRequest,
    service: MotionGenerationService = Depends(get_motion_generation_service),
) -> EnrichedPromptResponse:
    export = await service.generate_enriched_prompt(
        prompt=request.prompt,
        skeleton_preset=request.skeleton_preset,
        motion_spec=request.motion_spec,
    )
    return EnrichedPromptResponse(export=export)


@router.get("/api/prompt-exports/{export_id}", response_model=EnrichedPromptResponse)
async def get_prompt_export(
    export_id: str,
    service: MotionGenerationService = Depends(get_motion_generation_service),
) -> EnrichedPromptResponse:
    export = service.get_prompt_export(export_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Prompt export not found")
    return EnrichedPromptResponse(export=export)


@router.post("/api/runtime/respond", response_model=RuntimeRespondResponse)
async def runtime_respond(
    request: RuntimeRespondRequest,
    service: RuntimeCharacterService = Depends(get_runtime_character_service),
) -> RuntimeRespondResponse:
    reply, behavior = await service.respond(
        message=request.message,
        scene_context=request.scene_context,
        character_id=request.character_id,
    )
    return RuntimeRespondResponse(reply=reply, behavior=behavior)
