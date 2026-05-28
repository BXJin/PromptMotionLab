from __future__ import annotations

import io
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WavTrimResult:
    original_duration_seconds: float
    trimmed_duration_seconds: float
    trimmed: bool


def trim_wav_file_to_duration(path: Path, max_duration_seconds: float) -> WavTrimResult:
    if max_duration_seconds <= 0.0:
        return _duration_result(path, trimmed=False)

    with wave.open(str(path), "rb") as reader:
        channels = reader.getnchannels()
        sample_width = reader.getsampwidth()
        frame_rate = reader.getframerate()
        frame_count = reader.getnframes()
        compression_type = reader.getcomptype()
        compression_name = reader.getcompname()
        frames = reader.readframes(frame_count)

    if frame_rate <= 0 or frame_count <= 0:
        return WavTrimResult(0.0, 0.0, False)

    original_duration = frame_count / float(frame_rate)
    target_frames = int(max_duration_seconds * frame_rate)
    target_frames = max(1, min(target_frames, frame_count))
    if target_frames >= frame_count:
        return WavTrimResult(original_duration, original_duration, False)

    frame_size = channels * sample_width
    trimmed_frames = frames[: target_frames * frame_size]

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(sample_width)
        writer.setframerate(frame_rate)
        writer.setcomptype(compression_type, compression_name)
        writer.writeframes(trimmed_frames)

    path.write_bytes(buffer.getvalue())
    trimmed_duration = target_frames / float(frame_rate)
    return WavTrimResult(original_duration, trimmed_duration, True)


def _duration_result(path: Path, *, trimmed: bool) -> WavTrimResult:
    with wave.open(str(path), "rb") as reader:
        frame_rate = reader.getframerate()
        frame_count = reader.getnframes()
    duration = frame_count / float(frame_rate) if frame_rate > 0 else 0.0
    return WavTrimResult(duration, duration, trimmed)
