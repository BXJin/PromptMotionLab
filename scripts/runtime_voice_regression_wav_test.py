from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_CASES_PATH = (
    Path("Docs") / "Plan" / "10-RuntimeCharacter" / "runtime_voice_regression_cases.json"
)


@dataclass(frozen=True)
class VoiceRegressionResult:
    case_id: str
    status: str
    text: str
    wav_path: str
    tts_ms: int
    download_ms: int
    stt_ms: int
    provider: str
    model: str
    tts_provider: str
    tts_model: str
    duration_seconds: float
    viseme_count: int
    transcript: str
    issues: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate PromptMotion voice regression WAV files and optionally run STT checks."
    )
    parser.add_argument("--base-url", default="http://localhost:8010", help="FastAPI server base URL")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH, help="voice regression case JSON")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("Build") / "reports" / "voice_regression",
        help="output report/audio directory",
    )
    parser.add_argument("--voice", default="", help="optional TTS voice override")
    parser.add_argument("--skip-stt", action="store_true", help="only generate WAV files")
    parser.add_argument(
        "--write-matrix-cases",
        action="store_true",
        help="write a runtime_character_matrix-compatible cases JSON from generated transcripts",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    cases = load_cases(args.cases)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.out_dir / timestamp
    wav_dir = run_dir / "wav"
    wav_dir.mkdir(parents=True, exist_ok=True)

    results: list[VoiceRegressionResult] = []
    raw_payloads: list[dict[str, Any]] = []

    for case in cases:
        result, payload = run_case(
            base_url=base_url,
            case=case,
            wav_dir=wav_dir,
            voice=args.voice.strip() or None,
            skip_stt=args.skip_stt,
        )
        results.append(result)
        raw_payloads.append(payload)
        print_result(result)

    csv_path = run_dir / f"voice_regression_{timestamp}.csv"
    json_path = run_dir / f"voice_regression_{timestamp}.json"
    summary_path = run_dir / f"voice_regression_{timestamp}_summary.json"
    write_csv(csv_path, results)
    json_path.write_text(json.dumps(raw_payloads, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(build_summary(results), ensure_ascii=False, indent=2), encoding="utf-8")

    matrix_path = None
    if args.write_matrix_cases:
        matrix_path = run_dir / f"runtime_character_matrix_cases_from_voice_{timestamp}.json"
        write_matrix_cases(matrix_path, cases, results)

    print()
    print(f"WAV:     {wav_dir}")
    print(f"CSV:     {csv_path}")
    print(f"JSON:    {json_path}")
    print(f"Summary: {summary_path}")
    if matrix_path is not None:
        print(f"Matrix:  {matrix_path}")

    return 1 if any(result.status != "pass" for result in results) else 0


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("cases file must contain a JSON array")

    cases: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            raise ValueError("each voice case must be an object with a text field")
        case = dict(item)
        case["id"] = str(case.get("id") or f"voice_case_{index}")
        cases.append(case)
    return cases


def run_case(
    *,
    base_url: str,
    case: dict[str, Any],
    wav_dir: Path,
    voice: str | None,
    skip_stt: bool,
) -> tuple[VoiceRegressionResult, dict[str, Any]]:
    text = str(case["text"])
    case_id = str(case["id"])
    issues: list[str] = []

    try:
        tts_started = time.perf_counter()
        tts_payload = synthesize_tts(base_url, text, str(case.get("ttsStyle") or "warm"), voice)
        tts_ms = elapsed_ms(tts_started)
        speech_timeline = tts_payload.get("speechTimeline") or {}
        audio = speech_timeline.get("audio") or {}
        audio_url = str(audio.get("url") or "")
        if not audio_url:
            raise ValueError("TTS response missing speechTimeline.audio.url")

        wav_path = wav_dir / f"{slugify(case_id)}.wav"
        download_started = time.perf_counter()
        wav_bytes = download_bytes(urljoin(base_url + "/", audio_url.lstrip("/")))
        wav_path.write_bytes(wav_bytes)
        download_ms = elapsed_ms(download_started)
    except Exception as exc:
        issues.append(f"tts_or_download_failed:{exc.__class__.__name__}:{exc}")
        return make_result(case, "error", "", -1, -1, -1, "", "", "", "", -1.0, 0, "", issues), {
            "case": case,
            "error": issues[-1],
        }

    transcript = ""
    stt_ms = -1
    stt_provider = ""
    stt_model = ""
    if not skip_stt:
        try:
            stt_started = time.perf_counter()
            stt_payload = transcribe_wav(base_url, wav_bytes)
            stt_ms = elapsed_ms(stt_started)
            transcript = str(stt_payload.get("text") or "")
            stt_provider = str(stt_payload.get("provider") or "")
            stt_model = str(stt_payload.get("model") or "")
            issues.extend(evaluate_transcript(case, transcript))
        except Exception as exc:
            issues.append(f"stt_failed:{exc.__class__.__name__}:{exc}")

    result = make_result(
        case,
        "pass" if not issues else "fail",
        str(wav_path),
        tts_ms,
        download_ms,
        stt_ms,
        stt_provider,
        stt_model,
        str(speech_timeline.get("provider") or ""),
        str(speech_timeline.get("model") or ""),
        float(audio.get("durationSeconds", -1.0)),
        len(speech_timeline.get("visemes") or []),
        transcript,
        issues,
    )
    return result, {
        "case": case,
        "tts": tts_payload,
        "wavPath": str(wav_path),
        "stt": None if skip_stt else {"text": transcript, "provider": stt_provider, "model": stt_model},
        "issues": issues,
    }


def synthesize_tts(base_url: str, text: str, tts_style: str, voice: str | None) -> dict[str, Any]:
    body: dict[str, Any] = {"text": text, "ttsStyle": tts_style}
    if voice:
        body["voice"] = voice
    return post_json(f"{base_url}/api/runtime/tts/synthesize", body, timeout=30)


def transcribe_wav(base_url: str, wav_bytes: bytes) -> dict[str, Any]:
    request = Request(
        f"{base_url}/api/runtime/stt/transcribe?language=ko",
        data=wav_bytes,
        headers={"Content-Type": "audio/wav"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, body: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def download_bytes(url: str) -> bytes:
    with urlopen(url, timeout=30) as response:
        return response.read()


def evaluate_transcript(case: dict[str, Any], transcript: str) -> list[str]:
    issues: list[str] = []
    if not transcript:
        issues.append("empty_transcript")
        return issues

    expected_any = case.get("expectedTranscriptContainsAny")
    if expected_any:
        values = [str(item).lower() for item in expected_any]
        normalized = transcript.lower()
        if not any(value in normalized for value in values):
            issues.append(f"transcript_missing_any:{expected_any}")
    return issues


def make_result(
    case: dict[str, Any],
    status: str,
    wav_path: str,
    tts_ms: int,
    download_ms: int,
    stt_ms: int,
    provider: str,
    model: str,
    tts_provider: str,
    tts_model: str,
    duration_seconds: float,
    viseme_count: int,
    transcript: str,
    issues: list[str],
) -> VoiceRegressionResult:
    return VoiceRegressionResult(
        case_id=str(case["id"]),
        status=status,
        text=str(case["text"]),
        wav_path=wav_path,
        tts_ms=tts_ms,
        download_ms=download_ms,
        stt_ms=stt_ms,
        provider=provider,
        model=model,
        tts_provider=tts_provider,
        tts_model=tts_model,
        duration_seconds=duration_seconds,
        viseme_count=viseme_count,
        transcript=transcript,
        issues=";".join(issues),
    )


def write_csv(path: Path, results: list[VoiceRegressionResult]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(VoiceRegressionResult.__dataclass_fields__.keys()))
        writer.writeheader()
        for result in results:
            writer.writerow(result.__dict__)


def write_matrix_cases(path: Path, cases: list[dict[str, Any]], results: list[VoiceRegressionResult]) -> None:
    matrix_cases: list[dict[str, Any]] = []
    by_id = {result.case_id: result for result in results}
    for case in cases:
        result = by_id.get(str(case["id"]))
        message = result.transcript if result and result.transcript else str(case["text"])
        matrix_cases.append(
            {
                "id": str(case["id"]),
                "message": message,
                "sceneContext": case.get("sceneContext", {}),
            }
        )
    path.write_text(json.dumps(matrix_cases, ensure_ascii=False, indent=2), encoding="utf-8")


def build_summary(results: list[VoiceRegressionResult]) -> dict[str, Any]:
    return {
        "total": len(results),
        "passed": sum(1 for result in results if result.status == "pass"),
        "failed": sum(1 for result in results if result.status != "pass"),
        "avgTtsMs": average([result.tts_ms for result in results if result.tts_ms >= 0]),
        "avgSttMs": average([result.stt_ms for result in results if result.stt_ms >= 0]),
        "maxSttMs": max([result.stt_ms for result in results if result.stt_ms >= 0], default=-1),
    }


def print_result(result: VoiceRegressionResult) -> None:
    print(
        f"[{result.status.upper()}] {result.case_id} tts={result.tts_ms}ms "
        f"stt={result.stt_ms}ms duration={result.duration_seconds:.2f}s"
    )
    print(f"  wav: {result.wav_path}")
    if result.transcript:
        print(f"  stt: {result.transcript}")
    if result.issues:
        print(f"  issues: {result.issues}")


def average(values: list[int]) -> int:
    if not values:
        return -1
    return int(sum(values) / len(values))


def elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def slugify(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return safe.strip("._") or "case"


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        sys.exit(2)
