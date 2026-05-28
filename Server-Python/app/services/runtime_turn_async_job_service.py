import asyncio
import logging
import re
import uuid
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic

from app.contracts.requests import RuntimeRespondRequest
from app.contracts.runtime_behavior import BehaviorJson
from app.contracts.speech_timeline import SpeechAudio, SpeechSegment, SpeechTimeline
from app.services.runtime_async_job_service import RuntimeAsyncJobService
from app.services.runtime_character_service import RuntimeCharacterResult, RuntimeCharacterService
from app.services.service_limits import ServiceBusyError
from app.services.tts_service import TtsService

logger = logging.getLogger(__name__)


class RuntimeTurnJobStatus(StrEnum):
    PENDING = "pending"
    RESPONDING = "responding"
    SYNTHESIZING = "synthesizing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class RuntimeTurnAsyncJob:
    turn_job_id: str
    status: RuntimeTurnJobStatus
    request: RuntimeRespondRequest
    created_at: float
    updated_at: float
    reaction: BehaviorJson
    response_result: RuntimeCharacterResult | None = None
    speech_timeline: SpeechTimeline | None = None
    error: str | None = None


class RuntimeTurnAsyncJobService:
    def __init__(
        self,
        runtime_service: RuntimeCharacterService,
        tts_service: TtsService,
        *,
        max_jobs: int = 256,
        ttl_seconds: float = 300.0,
        prune_interval_seconds: float = 5.0,
        job_timeout_seconds: float = 20.0,
        max_in_flight: int = 64,
        segment_tts_enabled: bool = True,
        max_tts_segments: int = 4,
    ) -> None:
        self._runtime_service = runtime_service
        self._tts_service = tts_service
        self._max_jobs = max_jobs
        self._max_in_flight = max(0, max_in_flight)
        self._ttl_seconds = ttl_seconds
        self._job_timeout_seconds = job_timeout_seconds
        self._segment_tts_enabled = segment_tts_enabled
        self._max_tts_segments = max(1, max_tts_segments)
        self._jobs: dict[str, RuntimeTurnAsyncJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()
        del prune_interval_seconds

    async def submit(self, request: RuntimeRespondRequest) -> RuntimeTurnAsyncJob:
        now = monotonic()
        job = RuntimeTurnAsyncJob(
            turn_job_id=f"turn_{uuid.uuid4().hex[:12]}",
            status=RuntimeTurnJobStatus.PENDING,
            request=request,
            created_at=now,
            updated_at=now,
            reaction=RuntimeAsyncJobService.create_immediate_reaction(),
        )

        async with self._lock:
            if self._max_in_flight > 0 and self._active_count_locked() >= self._max_in_flight:
                raise ServiceBusyError(f"runtime turn queue is full: {self._max_in_flight}")
            self._jobs[job.turn_job_id] = job
            self._prune_overflow_locked()

        task = asyncio.create_task(self._run_job_with_timeout(job.turn_job_id))
        self._tasks[job.turn_job_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(job.turn_job_id, None))
        return job

    async def get(self, turn_job_id: str) -> RuntimeTurnAsyncJob | None:
        async with self._lock:
            return self._jobs.get(turn_job_id)

    async def prune_expired(self) -> None:
        async with self._lock:
            self._prune_locked(monotonic())

    async def shutdown(self) -> None:
        async with self._lock:
            for job in self._jobs.values():
                if job.status in {
                    RuntimeTurnJobStatus.PENDING,
                    RuntimeTurnJobStatus.RESPONDING,
                    RuntimeTurnJobStatus.SYNTHESIZING,
                }:
                    job.status = RuntimeTurnJobStatus.FAILED
                    job.error = "CancelledError: server shutdown"
                    job.updated_at = monotonic()

        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    async def _run_job_with_timeout(self, turn_job_id: str) -> None:
        try:
            await asyncio.wait_for(self._run_job(turn_job_id), timeout=self._job_timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning(
                "Runtime turn async job timed out. turn_job_id=%s timeout=%.2fs",
                turn_job_id,
                self._job_timeout_seconds,
            )
            await self._mark_failed(turn_job_id, f"TimeoutError: exceeded {self._job_timeout_seconds:.2f}s")
        except asyncio.CancelledError:
            await self._mark_failed(turn_job_id, "CancelledError: server shutdown")
            raise

    async def _run_job(self, turn_job_id: str) -> None:
        async with self._lock:
            job = self._jobs.get(turn_job_id)
            if job is None:
                return
            job.status = RuntimeTurnJobStatus.RESPONDING
            job.updated_at = monotonic()
            request = job.request

        try:
            response_result = await self._runtime_service.respond(
                message=request.message,
                scene_context=request.scene_context,
                character_id=request.character_id,
                session_id=request.session_id,
            )
        except Exception as exc:
            logger.exception("Runtime turn async job response step failed. turn_job_id=%s", turn_job_id)
            await self._mark_failed(turn_job_id, f"{exc.__class__.__name__}: {exc}")
            return

        async with self._lock:
            job = self._jobs.get(turn_job_id)
            if job is None:
                return
            job.response_result = response_result
            job.status = RuntimeTurnJobStatus.SYNTHESIZING
            job.updated_at = monotonic()

        try:
            if self._segment_tts_enabled:
                speech_timeline = await self._synthesize_segmented_turn(turn_job_id, response_result)
            else:
                speech_timeline = await self._tts_service.synthesize(
                    text=response_result.reply,
                    tts_style=response_result.behavior.tts_style,
                )
        except Exception as exc:
            logger.exception("Runtime turn async job TTS step failed. turn_job_id=%s", turn_job_id)
            await self._mark_failed(turn_job_id, f"{exc.__class__.__name__}: {exc}")
            return

        async with self._lock:
            job = self._jobs.get(turn_job_id)
            if job is not None:
                job.speech_timeline = speech_timeline
                job.status = RuntimeTurnJobStatus.SUCCEEDED
                job.updated_at = monotonic()
                logger.info("Runtime turn async job succeeded. turn_job_id=%s", turn_job_id)

    async def _synthesize_segmented_turn(
        self,
        turn_job_id: str,
        response_result: RuntimeCharacterResult,
    ) -> SpeechTimeline:
        texts = self._split_tts_segments(response_result.reply)
        if len(texts) <= 1:
            text = texts[0] if texts else response_result.reply.strip()
            speech_timeline = await self._tts_service.synthesize(
                text=text,
                tts_style=response_result.behavior.tts_style,
            )
            speech_timeline.segments = [
                self._create_speech_segment(speech_timeline, index=0, text=text, start_time=0.0)
            ]
            return speech_timeline

        segments: list[SpeechSegment] = []
        group_timeline: SpeechTimeline | None = None
        cumulative_start = 0.0
        total_tts_latency_ms = 0

        for index, text in enumerate(texts):
            segment_timeline = await self._tts_service.synthesize(
                text=text,
                tts_style=response_result.behavior.tts_style,
            )
            segment = self._create_speech_segment(
                segment_timeline,
                index=index,
                text=text,
                start_time=cumulative_start,
            )
            segments.append(segment)
            cumulative_start += segment.duration_seconds
            total_tts_latency_ms += segment.tts_latency_ms

            if group_timeline is None:
                group_timeline = SpeechTimeline(
                    utteranceId=f"uttgrp_{uuid.uuid4().hex[:12]}",
                    audio=segment_timeline.audio,
                    visemes=segment_timeline.visemes,
                    segments=list(segments),
                    provider=segment_timeline.provider,
                    model=segment_timeline.model,
                    ttsLatencyMs=total_tts_latency_ms,
                )
                await self._set_partial_speech_timeline(turn_job_id, group_timeline)
            else:
                group_timeline.segments = list(segments)
                group_timeline.tts_latency_ms = total_tts_latency_ms
                await self._set_partial_speech_timeline(turn_job_id, group_timeline)

        if group_timeline is None:
            raise RuntimeError("Segmented TTS did not produce a speech timeline")
        return group_timeline

    @staticmethod
    def _create_speech_segment(
        speech_timeline: SpeechTimeline,
        *,
        index: int,
        text: str,
        start_time: float,
    ) -> SpeechSegment:
        return SpeechSegment(
            segmentId=f"{speech_timeline.utterance_id}_seg_{index}",
            index=index,
            text=text,
            startTime=start_time,
            durationSeconds=speech_timeline.audio.duration_seconds,
            audio=speech_timeline.audio,
            visemes=speech_timeline.visemes,
            ttsLatencyMs=speech_timeline.tts_latency_ms,
        )

    async def _set_partial_speech_timeline(self, turn_job_id: str, speech_timeline: SpeechTimeline) -> None:
        async with self._lock:
            job = self._jobs.get(turn_job_id)
            if job is not None and job.status == RuntimeTurnJobStatus.SYNTHESIZING:
                job.speech_timeline = speech_timeline
                job.updated_at = monotonic()

    def _split_tts_segments(self, text: str) -> list[str]:
        normalized = " ".join(text.strip().split())
        if not normalized:
            return []

        parts = [
            part.strip()
            for part in re.split(r"(?<=[.!?。！？])\s+", normalized)
            if part.strip()
        ]
        if not parts:
            return [normalized]
        if len(parts) <= self._max_tts_segments:
            return parts

        head = parts[: self._max_tts_segments - 1]
        tail = " ".join(parts[self._max_tts_segments - 1 :])
        return [*head, tail]

    async def _mark_failed(self, turn_job_id: str, error: str) -> None:
        async with self._lock:
            job = self._jobs.get(turn_job_id)
            if job is not None:
                job.status = RuntimeTurnJobStatus.FAILED
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
            self._cancel_task(job.turn_job_id)
            self._jobs.pop(job.turn_job_id, None)

    def _active_count_locked(self) -> int:
        return sum(
            1
            for job in self._jobs.values()
            if job.status in {
                RuntimeTurnJobStatus.PENDING,
                RuntimeTurnJobStatus.RESPONDING,
                RuntimeTurnJobStatus.SYNTHESIZING,
            }
        )

    def _cancel_task(self, turn_job_id: str) -> None:
        task = self._tasks.pop(turn_job_id, None)
        if task is not None and not task.done():
            task.cancel()
