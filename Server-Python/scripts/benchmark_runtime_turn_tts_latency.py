import asyncio
import time
from pathlib import Path

from app.contracts.requests import RuntimeRespondRequest
from app.contracts.runtime_behavior import BehaviorJson, RuntimeTtsStyle, SceneContext
from app.providers.runtime import RuntimeBehaviorProvider
from app.providers.tts.base import TtsProvider, TtsResult
from app.services import RuntimeCharacterService, RuntimeTurnAsyncJobService, TtsService


class FixedReplyProvider(RuntimeBehaviorProvider):
    def __init__(self, reply: str) -> None:
        self._reply = reply

    async def respond(
        self,
        message: str,
        scene_context: SceneContext,
        character_id: str,
        conversation_history: list | None = None,
        character_profile: object | None = None,
    ) -> tuple[str, BehaviorJson]:
        del message, scene_context, character_id, conversation_history, character_profile
        return self._reply, BehaviorJson(intent="answer", emotion="friendly", ttsStyle=RuntimeTtsStyle.WARM)


class LengthScaledTtsProvider(TtsProvider):
    provider_name = "LengthScaledTtsProvider"
    model_name = "delay-by-text-length"

    async def synthesize(
        self,
        *,
        text: str,
        output_path: Path,
        tts_style: RuntimeTtsStyle,
        voice: str | None = None,
    ) -> TtsResult:
        del tts_style, voice
        await asyncio.sleep(0.02 + len(text) * 0.003)
        return TtsResult(
            audio_path=output_path,
            duration_seconds=max(0.2, len(text) / 16.0),
            visemes=[],
            provider=self.provider_name,
            model=self.model_name,
        )


class TailDelayTtsProvider(TtsProvider):
    provider_name = "TailDelayTtsProvider"
    model_name = "parallel-tail-check"

    async def synthesize(
        self,
        *,
        text: str,
        output_path: Path,
        tts_style: RuntimeTtsStyle,
        voice: str | None = None,
    ) -> TtsResult:
        del tts_style, voice
        await asyncio.sleep(0.03 if text == "짧아." else 0.12)
        return TtsResult(
            audio_path=output_path,
            duration_seconds=0.2,
            visemes=[],
            provider=self.provider_name,
            model=self.model_name,
        )


async def measure(segment_tts_enabled: bool, reply: str) -> tuple[int, int, int]:
    service = RuntimeTurnAsyncJobService(
        RuntimeCharacterService(primary_provider=FixedReplyProvider(reply)),
        TtsService(
            provider=LengthScaledTtsProvider(),
            fallback_provider=LengthScaledTtsProvider(),
            provider_timeout_seconds=2,
            fallback_timeout_seconds=2,
        ),
        segment_tts_enabled=segment_tts_enabled,
    )
    job = await service.submit(RuntimeRespondRequest(message="오늘 영화 봤어", characterId="default_girl"))
    started = time.perf_counter()
    first_timeline_ms = -1
    segment_count = 0
    deadline = started + 3.0

    while time.perf_counter() < deadline:
        current = await service.get(job.turn_job_id)
        if current is None:
            await asyncio.sleep(0.005)
            continue
        if first_timeline_ms < 0 and current.speech_timeline is not None:
            first_timeline_ms = int((time.perf_counter() - started) * 1000)
            segment_count = len(current.speech_timeline.segments)
        if current.status == "succeeded":
            total_ms = int((time.perf_counter() - started) * 1000)
            final_segments = len(current.speech_timeline.segments) if current.speech_timeline else segment_count
            return first_timeline_ms, total_ms, final_segments
        await asyncio.sleep(0.005)

    raise TimeoutError("runtime turn benchmark timed out")


async def measure_parallel_tail() -> tuple[int, int, int]:
    reply = "짧아. 두 번째 문장은 조금 길게 말해볼게. 세 번째 문장도 비슷하게 길게 말해볼게."
    service = RuntimeTurnAsyncJobService(
        RuntimeCharacterService(primary_provider=FixedReplyProvider(reply)),
        TtsService(
            provider=TailDelayTtsProvider(),
            fallback_provider=TailDelayTtsProvider(),
            provider_timeout_seconds=2,
            fallback_timeout_seconds=2,
        ),
        segment_tts_enabled=True,
    )
    job = await service.submit(RuntimeRespondRequest(message="오늘 영화 봤어", characterId="default_girl"))
    started = time.perf_counter()
    first_timeline_ms = -1
    segment_count = 0
    deadline = started + 3.0

    while time.perf_counter() < deadline:
        current = await service.get(job.turn_job_id)
        if current is None:
            await asyncio.sleep(0.005)
            continue
        if first_timeline_ms < 0 and current.speech_timeline is not None:
            first_timeline_ms = int((time.perf_counter() - started) * 1000)
            segment_count = len(current.speech_timeline.segments)
        if current.status == "succeeded":
            total_ms = int((time.perf_counter() - started) * 1000)
            final_segments = len(current.speech_timeline.segments) if current.speech_timeline else segment_count
            return first_timeline_ms, total_ms, final_segments
        await asyncio.sleep(0.005)

    raise TimeoutError("parallel tail benchmark timed out")


async def main() -> None:
    reply = "안녕. 오늘 영화 봤어? 재밌었어!"
    full_first_ms, full_total_ms, full_segments = await measure(False, reply)
    seg_first_ms, seg_total_ms, seg_segments = await measure(True, reply)
    tail_first_ms, tail_total_ms, tail_segments = await measure_parallel_tail()

    print("mode,first_timeline_ms,total_ms,segments")
    print(f"full_turn_tts,{full_first_ms},{full_total_ms},{full_segments}")
    print(f"segmented_tts,{seg_first_ms},{seg_total_ms},{seg_segments}")
    print(f"parallel_remaining_segments,{tail_first_ms},{tail_total_ms},{tail_segments}")
    if full_first_ms > 0 and seg_first_ms > 0:
        saved = full_first_ms - seg_first_ms
        print(f"first_timeline_saved_ms,{saved}")
    legacy_tail_estimate_ms = 30 + 120 + 120
    print(f"legacy_sequential_remaining_estimate_ms,{legacy_tail_estimate_ms}")
    print(f"parallel_remaining_saved_estimate_ms,{legacy_tail_estimate_ms - tail_total_ms}")


if __name__ == "__main__":
    asyncio.run(main())
