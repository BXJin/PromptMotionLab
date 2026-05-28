import asyncio
import logging
import uuid
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic

from app.contracts.speech_timeline import SpeechTimeline
from app.contracts.tts import TtsSynthesizeRequest
from app.services.service_limits import ServiceBusyError
from app.services.tts_service import TtsService

logger = logging.getLogger(__name__)


class TtsJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class TtsAsyncJob:
    job_id: str
    status: TtsJobStatus
    request: TtsSynthesizeRequest
    created_at: float
    updated_at: float
    result: SpeechTimeline | None = None
    error: str | None = None


class TtsAsyncJobService:
    def __init__(
        self,
        tts_service: TtsService,
        *,
        max_jobs: int = 256,
        ttl_seconds: float = 300.0,
        prune_interval_seconds: float = 5.0,
        job_timeout_seconds: float = 15.0,
        max_in_flight: int = 64,
    ) -> None:
        self._tts_service = tts_service
        self._max_jobs = max_jobs
        self._max_in_flight = max(0, max_in_flight)
        self._ttl_seconds = ttl_seconds
        self._job_timeout_seconds = job_timeout_seconds
        self._jobs: dict[str, TtsAsyncJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()
        del prune_interval_seconds

    async def submit(self, request: TtsSynthesizeRequest) -> TtsAsyncJob:
        now = monotonic()
        job = TtsAsyncJob(
            job_id=f"tts_{uuid.uuid4().hex[:12]}",
            status=TtsJobStatus.PENDING,
            request=request,
            created_at=now,
            updated_at=now,
        )

        async with self._lock:
            if self._max_in_flight > 0 and self._active_count_locked() >= self._max_in_flight:
                raise ServiceBusyError(f"tts queue is full: {self._max_in_flight}")
            self._jobs[job.job_id] = job
            self._prune_overflow_locked()

        task = asyncio.create_task(self._run_job_with_timeout(job.job_id))
        self._tasks[job.job_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(job.job_id, None))
        return job

    async def get(self, job_id: str) -> TtsAsyncJob | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def prune_expired(self) -> None:
        async with self._lock:
            self._prune_locked(monotonic())

    async def shutdown(self) -> None:
        async with self._lock:
            for job in self._jobs.values():
                if job.status in {TtsJobStatus.PENDING, TtsJobStatus.RUNNING}:
                    job.status = TtsJobStatus.FAILED
                    job.error = "CancelledError: server shutdown"
                    job.updated_at = monotonic()

        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    async def _run_job_with_timeout(self, job_id: str) -> None:
        try:
            await asyncio.wait_for(self._run_job(job_id), timeout=self._job_timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning("TTS async job timed out. job_id=%s timeout=%.2fs", job_id, self._job_timeout_seconds)
            await self._mark_failed(job_id, f"TimeoutError: exceeded {self._job_timeout_seconds:.2f}s")
        except asyncio.CancelledError:
            await self._mark_failed(job_id, "CancelledError: server shutdown")
            raise

    async def _run_job(self, job_id: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = TtsJobStatus.RUNNING
            job.updated_at = monotonic()
            request = job.request

        try:
            result = await self._tts_service.synthesize(
                text=request.text,
                tts_style=request.tts_style,
                voice=request.voice,
            )
        except Exception as exc:
            logger.exception("TTS async job failed. job_id=%s", job_id)
            await self._mark_failed(job_id, f"{exc.__class__.__name__}: {exc}")
            return

        async with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.status = TtsJobStatus.SUCCEEDED
                job.result = result
                job.updated_at = monotonic()
                logger.info("TTS async job succeeded. job_id=%s", job_id)

    async def _mark_failed(self, job_id: str, error: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.status = TtsJobStatus.FAILED
                job.error = error
                job.updated_at = monotonic()

    def _prune_locked(self, now: float) -> None:
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if now - job.updated_at > self._ttl_seconds
        ]
        for job_id in expired:
            self._cancel_task(job_id)
            self._jobs.pop(job_id, None)

        self._prune_overflow_locked()

    def _prune_overflow_locked(self) -> None:
        if len(self._jobs) <= self._max_jobs:
            return

        overflow = len(self._jobs) - self._max_jobs
        oldest = sorted(self._jobs.values(), key=lambda job: job.updated_at)[:overflow]
        for job in oldest:
            self._cancel_task(job.job_id)
            self._jobs.pop(job.job_id, None)

    def _cancel_task(self, job_id: str) -> None:
        task = self._tasks.pop(job_id, None)
        if task is not None and not task.done():
            task.cancel()

    def _active_count_locked(self) -> int:
        return sum(
            1
            for job in self._jobs.values()
            if job.status in {TtsJobStatus.PENDING, TtsJobStatus.RUNNING}
        )
