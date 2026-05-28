import asyncio
import contextlib
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.dependencies import (
    get_runtime_async_job_service,
    get_runtime_turn_async_job_service,
    get_tts_async_job_service,
    get_tts_service,
)
from app.security import BodySizeLimitMiddleware, RateLimitMiddleware


async def _prune_async_jobs_loop(interval_seconds: float) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        await get_runtime_async_job_service().prune_expired()
        await get_runtime_turn_async_job_service().prune_expired()
        await get_tts_async_job_service().prune_expired()
        await get_tts_service().cleanup_audio_files(
            ttl_seconds=float(os.getenv("TTS_AUDIO_TTL_SECONDS", "600")),
            max_files=int(os.getenv("TTS_AUDIO_MAX_FILES", "512")),
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    del app
    interval_seconds = float(os.getenv("ASYNC_JOB_PRUNE_BACKGROUND_INTERVAL_SECONDS", "15"))
    task = asyncio.create_task(_prune_async_jobs_loop(interval_seconds))
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await get_runtime_async_job_service().shutdown()
        await get_runtime_turn_async_job_service().shutdown()
        await get_tts_async_job_service().shutdown()


app = FastAPI(
    title="PromptMotionLab Server",
    version="0.1.0",
    description="MotionSpec, procedural gesture, and prompt export backend.",
    lifespan=lifespan,
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/docs",
    redoc_url=None if os.getenv("ENVIRONMENT") == "production" else "/redoc",
    openapi_url=None if os.getenv("ENVIRONMENT") == "production" else "/openapi.json",
)

app.add_middleware(
    RateLimitMiddleware,
    enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
    runtime_limit=int(os.getenv("RATE_LIMIT_RUNTIME_PER_MINUTE", "60")),
    runtime_job_poll_limit=int(os.getenv("RATE_LIMIT_RUNTIME_JOB_POLL_PER_MINUTE", "600")),
    runtime_stt_limit=int(os.getenv("RATE_LIMIT_RUNTIME_STT_PER_MINUTE", "60")),
    runtime_tts_limit=int(os.getenv("RATE_LIMIT_RUNTIME_TTS_PER_MINUTE", "120")),
    audio_limit=int(os.getenv("RATE_LIMIT_AUDIO_PER_MINUTE", "180")),
    window_seconds=float(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
)
app.add_middleware(
    BodySizeLimitMiddleware,
    limits={
        "/api/runtime/stt/transcribe": int(os.getenv("STT_MAX_AUDIO_BYTES", str(5 * 1024 * 1024))),
    },
)

app.include_router(router)
