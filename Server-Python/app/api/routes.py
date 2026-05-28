import json
import os
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse

from app.contracts import (
    AnalyzeIntentRequest,
    AnalyzeIntentResponse,
    EnrichedPromptRequest,
    EnrichedPromptResponse,
    HealthResponse,
    ProceduralGenerationRequest,
    ProceduralGenerationResponse,
    RuntimeAsyncRespondAcceptedResponse,
    RuntimeAsyncRespondJobResponse,
    RuntimeRespondRequest,
    RuntimeRespondResponse,
    RuntimeTurnAsyncAcceptedResponse,
    RuntimeTurnAsyncJobResponse,
    SttTranscribeResponse,
    TtsAsyncSynthesizeAcceptedResponse,
    TtsAsyncSynthesizeJobResponse,
    TtsSynthesizeRequest,
    TtsSynthesizeResponse,
)
from app.contracts.runtime_behavior import (
    BehaviorJson,
    RuntimeEmotion,
    RuntimeGestureKey,
    RuntimeGaze,
    RuntimeHeadMotion,
    RuntimeIntent,
    RuntimeTtsStyle,
)
from app.dependencies import (
    get_motion_generation_service,
    get_runtime_async_job_service,
    get_runtime_character_service,
    get_runtime_turn_async_job_service,
    get_stt_service,
    get_tts_async_job_service,
    get_tts_service,
)
from app.services import (
    MotionGenerationService,
    RuntimeAsyncJobService,
    RuntimeCharacterService,
    RuntimeTurnAsyncJobService,
    SttService,
    TtsAsyncJobService,
    TtsService,
)
from app.services.runtime_async_job_service import RuntimeJobStatus
from app.services.runtime_turn_async_job_service import RuntimeTurnJobStatus
from app.services.service_limits import ServiceBusyError
from app.services.tts_async_job_service import TtsJobStatus
from app.providers.stt.azure_streaming_provider import AzureSpeechStreamingSttSession
from app.security import WebSocketConnectionLimiter, client_key_from_websocket

router = APIRouter()
RETRY_AFTER_SECONDS = "5"
MAX_STT_AUDIO_BYTES = int(os.getenv("STT_MAX_AUDIO_BYTES", str(5 * 1024 * 1024)))
SUPPORTED_STT_SAMPLE_RATES = {8000, 16000, 24000, 48000}
SUPPORTED_STT_CONTENT_TYPES = {"audio/wav", "audio/x-wav", "application/octet-stream"}
RUNTIME_WS_LIMITER = WebSocketConnectionLimiter(
    max_total=int(os.getenv("WEBSOCKET_RUNTIME_MAX_TOTAL", "32")),
    max_per_client=int(os.getenv("WEBSOCKET_RUNTIME_MAX_PER_CLIENT", "2")),
)
STT_WS_LIMITER = WebSocketConnectionLimiter(
    max_total=int(os.getenv("WEBSOCKET_STT_MAX_TOTAL", "32")),
    max_per_client=int(os.getenv("WEBSOCKET_STT_MAX_PER_CLIENT", "2")),
)


def _is_plain_wav_filename(filename: str) -> bool:
    return filename.endswith(".wav") and "/" not in filename and "\\" not in filename and ".." not in filename


def _validate_stt_content_type(content_type: str) -> str:
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type not in SUPPORTED_STT_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported audio content type")
    return media_type


def _validate_stt_content_length(request: Request) -> None:
    content_length = request.headers.get("content-length")
    if content_length is None:
        return
    try:
        length = int(content_length)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Content-Length header") from exc
    if length > MAX_STT_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio body too large")


def _parse_stt_sample_rate(payload: dict) -> int:
    raw_sample_rate = payload.get("sampleRate") or 16000
    try:
        sample_rate = int(raw_sample_rate)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_sample_rate") from exc
    if sample_rate not in SUPPORTED_STT_SAMPLE_RATES:
        raise ValueError("unsupported_sample_rate")
    return sample_rate


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
    try:
        result = await service.respond(
            message=request.message,
            scene_context=request.scene_context,
            character_id=request.character_id,
            session_id=request.session_id,
        )
    except ServiceBusyError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": RETRY_AFTER_SECONDS},
        ) from exc
    return RuntimeRespondResponse(
        reply=result.reply,
        behavior=result.behavior,
        metadata=result.metadata,
    )


@router.post("/api/runtime/stt/transcribe", response_model=SttTranscribeResponse)
async def runtime_stt_transcribe(
    request: Request,
    language: str | None = None,
    service: SttService = Depends(get_stt_service),
) -> SttTranscribeResponse:
    content_type = _validate_stt_content_type(request.headers.get("content-type", "audio/wav"))
    _validate_stt_content_length(request)
    try:
        audio_bytes = await request.body()
        return await service.transcribe(
            audio_bytes=audio_bytes,
            content_type=content_type,
            language=language,
        )
    except ServiceBusyError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": RETRY_AFTER_SECONDS},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/runtime/respond/async", response_model=RuntimeAsyncRespondAcceptedResponse)
async def runtime_respond_async(
    request: RuntimeRespondRequest,
    service: RuntimeAsyncJobService = Depends(get_runtime_async_job_service),
) -> RuntimeAsyncRespondAcceptedResponse:
    try:
        job = await service.submit(request)
    except ServiceBusyError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": RETRY_AFTER_SECONDS},
        ) from exc
    return RuntimeAsyncRespondAcceptedResponse(
        jobId=job.job_id,
        status=job.status.value,
        reaction=job.reaction,
    )


@router.get("/api/runtime/respond/jobs/{job_id}", response_model=RuntimeAsyncRespondJobResponse)
async def runtime_respond_job(
    job_id: str,
    service: RuntimeAsyncJobService = Depends(get_runtime_async_job_service),
) -> RuntimeAsyncRespondJobResponse:
    job = await service.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Runtime job not found")

    response = None
    if job.result is not None:
        response = RuntimeRespondResponse(
            reply=job.result.reply,
            behavior=job.result.behavior,
            metadata=job.result.metadata,
        )

    return RuntimeAsyncRespondJobResponse(
        jobId=job.job_id,
        status=job.status.value if isinstance(job.status, RuntimeJobStatus) else str(job.status),
        response=response,
        error=job.error,
    )


@router.post("/api/runtime/turn/async", response_model=RuntimeTurnAsyncAcceptedResponse)
async def runtime_turn_async(
    request: RuntimeRespondRequest,
    service: RuntimeTurnAsyncJobService = Depends(get_runtime_turn_async_job_service),
) -> RuntimeTurnAsyncAcceptedResponse:
    try:
        job = await service.submit(request)
    except ServiceBusyError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": RETRY_AFTER_SECONDS},
        ) from exc
    return RuntimeTurnAsyncAcceptedResponse(
        turnJobId=job.turn_job_id,
        status=job.status.value,
        reaction=job.reaction,
    )


@router.get("/api/runtime/turn/jobs/{turn_job_id}", response_model=RuntimeTurnAsyncJobResponse)
async def runtime_turn_job(
    turn_job_id: str,
    service: RuntimeTurnAsyncJobService = Depends(get_runtime_turn_async_job_service),
) -> RuntimeTurnAsyncJobResponse:
    job = await service.get(turn_job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Runtime turn job not found")

    response = None
    if job.response_result is not None:
        response = RuntimeRespondResponse(
            reply=job.response_result.reply,
            behavior=job.response_result.behavior,
            metadata=job.response_result.metadata,
        )

    return RuntimeTurnAsyncJobResponse(
        turnJobId=job.turn_job_id,
        status=job.status.value if isinstance(job.status, RuntimeTurnJobStatus) else str(job.status),
        reaction=job.reaction,
        responseReady=job.response_result is not None,
        ttsReady=job.speech_timeline is not None,
        response=response,
        speechTimeline=job.speech_timeline,
        error=job.error,
    )


@router.post("/api/runtime/tts/synthesize", response_model=TtsSynthesizeResponse)
async def runtime_tts_synthesize(
    request: TtsSynthesizeRequest,
    service: TtsService = Depends(get_tts_service),
) -> TtsSynthesizeResponse:
    try:
        speech_timeline = await service.synthesize(
            text=request.text,
            tts_style=request.tts_style,
            voice=request.voice,
        )
    except ServiceBusyError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": RETRY_AFTER_SECONDS},
        ) from exc
    return TtsSynthesizeResponse(speechTimeline=speech_timeline)


@router.post("/api/runtime/tts/synthesize/async", response_model=TtsAsyncSynthesizeAcceptedResponse)
async def runtime_tts_synthesize_async(
    request: TtsSynthesizeRequest,
    service: TtsAsyncJobService = Depends(get_tts_async_job_service),
) -> TtsAsyncSynthesizeAcceptedResponse:
    try:
        job = await service.submit(request)
    except ServiceBusyError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": RETRY_AFTER_SECONDS},
        ) from exc
    return TtsAsyncSynthesizeAcceptedResponse(
        jobId=job.job_id,
        status=job.status.value,
    )


@router.get("/api/runtime/tts/jobs/{job_id}", response_model=TtsAsyncSynthesizeJobResponse)
async def runtime_tts_job(
    job_id: str,
    service: TtsAsyncJobService = Depends(get_tts_async_job_service),
) -> TtsAsyncSynthesizeJobResponse:
    job = await service.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="TTS job not found")

    return TtsAsyncSynthesizeJobResponse(
        jobId=job.job_id,
        status=job.status.value if isinstance(job.status, TtsJobStatus) else str(job.status),
        speechTimeline=job.result,
        error=job.error,
    )


@router.get("/api/runtime/audio/{filename}")
async def runtime_audio(
    filename: str,
    service: TtsService = Depends(get_tts_service),
) -> FileResponse:
    if not _is_plain_wav_filename(filename):
        raise HTTPException(status_code=404, detail="Audio file not found")
    path = service.resolve_audio_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(path, media_type="audio/wav", filename=filename)


@router.post("/api/runtime/respond/stream")
async def runtime_respond_stream(
    request: RuntimeRespondRequest,
    service: RuntimeCharacterService = Depends(get_runtime_character_service),
) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        reaction = BehaviorJson(
            emotion=RuntimeEmotion.THINKING,
            intensity=0.45,
            confidence=1.0,
            intent=RuntimeIntent.ANSWER,
            gaze=RuntimeGaze.USER,
            gestureKey=RuntimeGestureKey.SMALL_ACK,
            headMotion=RuntimeHeadMotion.THINKING_TILT,
            ttsStyle=RuntimeTtsStyle.NEUTRAL,
        )
        yield _sse(
            "reaction",
            {
                "type": "reaction",
                "behavior": reaction.model_dump(by_alias=True),
            },
        )

        try:
            result = await service.respond(
                message=request.message,
                scene_context=request.scene_context,
                character_id=request.character_id,
                session_id=request.session_id,
            )
        except ServiceBusyError as exc:
            yield _sse(
                "error",
                {
                    "type": "error",
                    "error": "service_busy",
                    "detail": str(exc),
                },
            )
            return
        response = RuntimeRespondResponse(
            reply=result.reply,
            behavior=result.behavior,
            metadata=result.metadata,
        )
        yield _sse(
            "final",
            {
                "type": "final",
                "response": response.model_dump(by_alias=True),
            },
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.websocket("/ws/runtime")
async def runtime_websocket(
    websocket: WebSocket,
    service: RuntimeCharacterService = Depends(get_runtime_character_service),
) -> None:
    client_key = client_key_from_websocket(websocket)
    if not await RUNTIME_WS_LIMITER.try_acquire(client_key):
        await websocket.close(code=1008, reason="connection_limit_exceeded")
        return
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                request = _parse_runtime_ws_request(payload)
            except Exception as exc:
                del exc
                await websocket.send_json(
                    {
                        "type": "error",
                        "requestId": "",
                        "error": "invalid_request",
                    }
                )
                continue

            request_id = str(payload.get("requestId") or "")
            await websocket.send_json(
                {
                    "type": "reaction",
                    "requestId": request_id,
                    "behavior": _immediate_reaction().model_dump(by_alias=True),
                }
            )

            try:
                result = await service.respond(
                    message=request.message,
                    scene_context=request.scene_context,
                    character_id=request.character_id,
                    session_id=request.session_id,
                )
                response = RuntimeRespondResponse(
                    reply=result.reply,
                    behavior=result.behavior,
                    metadata=result.metadata,
                )
                await websocket.send_json(
                    {
                        "type": "final",
                        "requestId": request_id,
                        "response": response.model_dump(by_alias=True),
                    }
                )
            except ServiceBusyError as exc:
                await websocket.send_json(
                    {
                        "type": "error",
                        "requestId": request_id,
                        "error": "service_busy",
                        "detail": str(exc),
                    }
                )
            except Exception as exc:
                del exc
                await websocket.send_json(
                    {
                        "type": "error",
                        "requestId": request_id,
                        "error": "runtime_failed",
                    }
                )
    except WebSocketDisconnect:
        return
    finally:
        await RUNTIME_WS_LIMITER.release(client_key)


@router.websocket("/ws/stt")
async def streaming_stt_websocket(websocket: WebSocket) -> None:
    client_key = client_key_from_websocket(websocket)
    if not await STT_WS_LIMITER.try_acquire(client_key):
        await websocket.close(code=1008, reason="connection_limit_exceeded")
        return
    await websocket.accept()
    session: AzureSpeechStreamingSttSession | None = None
    try:
        while True:
            message = await websocket.receive()
            if "text" in message and message["text"] is not None:
                payload = json.loads(message["text"])
                message_type = str(payload.get("type") or "")
                if message_type == "start":
                    session = _create_streaming_stt_session(payload)
                    await session.start()
                    await websocket.send_json({"type": "started"})
                elif message_type == "stop":
                    if session is not None:
                        await session.stop()
                        await _flush_streaming_stt_events(websocket, session, final_wait_seconds=1.0)
                    await websocket.send_json({"type": "stopped"})
                    return
                else:
                    await websocket.send_json({"type": "error", "error": "invalid_message_type"})
            elif "bytes" in message and message["bytes"] is not None:
                if session is None:
                    await websocket.send_json({"type": "error", "error": "stream_not_started"})
                    continue
                await session.write(message["bytes"])
                await _flush_streaming_stt_events(websocket, session)
    except WebSocketDisconnect:
        if session is not None:
            await session.stop()
    except Exception as exc:
        del exc
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.send_json({"type": "error", "error": "streaming_stt_failed"})
    finally:
        await STT_WS_LIMITER.release(client_key)


def _create_streaming_stt_session(payload: dict) -> AzureSpeechStreamingSttSession:
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")
    if not speech_key or not speech_region:
        raise RuntimeError("Azure Speech credentials are required for streaming STT")
    return AzureSpeechStreamingSttSession(
        speech_key=speech_key,
        speech_region=speech_region,
        language=str(payload.get("language") or os.getenv("AZURE_STT_LANGUAGE", "ko-KR")),
        sample_rate=_parse_stt_sample_rate(payload),
    )


async def _flush_streaming_stt_events(
    websocket: WebSocket,
    session: AzureSpeechStreamingSttSession,
    *,
    final_wait_seconds: float = 0.0,
) -> None:
    deadline = final_wait_seconds
    while True:
        event = await session.next_event(timeout_seconds=deadline)
        deadline = 0.0
        if event is None:
            return
        if event.type == "partial" and not event.text:
            continue
        if event.type == "final" and not event.text:
            continue
        await websocket.send_json(
            {
                "type": event.type,
                "text": event.text,
                "language": event.language,
                "sttLatencyMs": event.duration_ms,
                "provider": event.provider,
                "model": event.model,
                "error": event.error,
            }
        )


def _parse_runtime_ws_request(payload: dict) -> RuntimeRespondRequest:
    if payload.get("type") not in {None, "runtime_request"}:
        raise ValueError("type must be runtime_request")

    request_payload = {
        "characterId": payload.get("characterId", "default_guide"),
        "message": payload["message"],
        "sceneContext": payload.get("sceneContext", {}),
    }
    if payload.get("sessionId"):
        request_payload["sessionId"] = payload["sessionId"]
    return RuntimeRespondRequest.model_validate(request_payload)


def _immediate_reaction() -> BehaviorJson:
    return BehaviorJson(
        emotion=RuntimeEmotion.THINKING,
        intensity=0.45,
        confidence=1.0,
        intent=RuntimeIntent.ANSWER,
        gaze=RuntimeGaze.USER,
        gestureKey=RuntimeGestureKey.SMALL_ACK,
        headMotion=RuntimeHeadMotion.THINKING_TILT,
        ttsStyle=RuntimeTtsStyle.NEUTRAL,
    )
