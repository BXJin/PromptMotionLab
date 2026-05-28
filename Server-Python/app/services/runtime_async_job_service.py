import asyncio
import logging
import uuid
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic

from app.contracts.requests import RuntimeRespondRequest
from app.contracts.runtime_behavior import (
    BehaviorJson,
    RuntimeEmotion,
    RuntimeGestureKey,
    RuntimeGaze,
    RuntimeHeadMotion,
    RuntimeIntent,
    RuntimeTtsStyle,
)
from app.services.runtime_character_service import RuntimeCharacterResult, RuntimeCharacterService
from app.services.service_limits import ServiceBusyError

logger = logging.getLogger(__name__)


class RuntimeJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class RuntimeAsyncJob:
    job_id: str
    status: RuntimeJobStatus
    request: RuntimeRespondRequest
    created_at: float
    updated_at: float
    reaction: BehaviorJson
    result: RuntimeCharacterResult | None = None
    error: str | None = None


class RuntimeAsyncJobService:
    def __init__(
        self,
        runtime_service: RuntimeCharacterService,
        *,
        max_jobs: int = 256,
        ttl_seconds: float = 300.0,
        prune_interval_seconds: float = 5.0,
        job_timeout_seconds: float = 15.0,
        max_in_flight: int = 64,
    ) -> None:
        self._runtime_service = runtime_service
        self._max_jobs = max_jobs
        self._max_in_flight = max(0, max_in_flight)
        self._ttl_seconds = ttl_seconds
        self._job_timeout_seconds = job_timeout_seconds
        self._jobs: dict[str, RuntimeAsyncJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()
        del prune_interval_seconds

    async def submit(self, request: RuntimeRespondRequest) -> RuntimeAsyncJob:
        now = monotonic()
        job = RuntimeAsyncJob(
            job_id=f"rt_{uuid.uuid4().hex[:12]}",
            status=RuntimeJobStatus.PENDING,
            request=request,
            created_at=now,
            updated_at=now,
            reaction=self.create_immediate_reaction(),
        )

        async with self._lock:
            if self._max_in_flight > 0 and self._active_count_locked() >= self._max_in_flight:
                raise ServiceBusyError(f"runtime queue is full: {self._max_in_flight}")
            self._jobs[job.job_id] = job
            self._prune_overflow_locked()

        task = asyncio.create_task(self._run_job_with_timeout(job.job_id))
        self._tasks[job.job_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(job.job_id, None))
        return job

    async def get(self, job_id: str) -> RuntimeAsyncJob | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def prune_expired(self) -> None:
        async with self._lock:
            self._prune_locked(monotonic())

    async def shutdown(self) -> None:
        async with self._lock:
            for job in self._jobs.values():
                if job.status in {RuntimeJobStatus.PENDING, RuntimeJobStatus.RUNNING}:
                    job.status = RuntimeJobStatus.FAILED
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
            logger.warning("Runtime async job timed out. job_id=%s timeout=%.2fs", job_id, self._job_timeout_seconds)
            await self._mark_failed(job_id, f"TimeoutError: exceeded {self._job_timeout_seconds:.2f}s")
        except asyncio.CancelledError:
            await self._mark_failed(job_id, "CancelledError: server shutdown")
            raise

    async def _run_job(self, job_id: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = RuntimeJobStatus.RUNNING
            job.updated_at = monotonic()
            request = job.request

        try:
            result = await self._runtime_service.respond(
                message=request.message,
                scene_context=request.scene_context,
                character_id=request.character_id,
                session_id=request.session_id,
            )
        except Exception as exc:
            logger.exception("Runtime async job failed. job_id=%s", job_id)
            await self._mark_failed(job_id, f"{exc.__class__.__name__}: {exc}")
            return

        async with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.status = RuntimeJobStatus.SUCCEEDED
                job.result = result
                job.updated_at = monotonic()
                logger.info("Runtime async job succeeded. job_id=%s", job_id)

    async def _mark_failed(self, job_id: str, error: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.status = RuntimeJobStatus.FAILED
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
            if job.status in {RuntimeJobStatus.PENDING, RuntimeJobStatus.RUNNING}
        )

    @staticmethod
    def create_immediate_reaction() -> BehaviorJson:
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
