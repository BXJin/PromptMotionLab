from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_CASES = [
    "Hey, how are you today?",
    "Can you tell me more about your day?",
    "I'm sorry, I didn't mean to make you feel that way.",
    "What do you think I should do next?",
]


@dataclass(frozen=True)
class TurnFeelResult:
    case_id: str
    status: str
    message: str
    accepted_ms: int
    first_poll_ms: int
    response_ready_ms: int
    tts_ready_ms: int
    total_ms: int
    provider: str
    model: str
    fallback_used: bool
    reply: str
    emotion: str
    intent: str
    tts_duration_seconds: float
    viseme_count: int
    issues: str


def main() -> int:
    parser = argparse.ArgumentParser(description="PromptMotion realtime conversation feel test")
    parser.add_argument("--base-url", default="http://localhost:8010", help="FastAPI server base URL")
    parser.add_argument("--session-id", default="turn_feel_test", help="runtime session id")
    parser.add_argument("--character-id", default="default_girl", help="runtime character id")
    parser.add_argument("--cases", type=Path, help="optional JSON array of messages or case objects")
    parser.add_argument("--out-dir", type=Path, default=Path("Build") / "reports", help="output directory")
    parser.add_argument("--poll-ms", type=int, default=100, help="job polling interval in milliseconds")
    parser.add_argument("--timeout-seconds", type=float, default=25.0, help="per case timeout")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = args.out_dir / f"runtime_turn_feel_{timestamp}.csv"
    json_path = args.out_dir / f"runtime_turn_feel_{timestamp}.json"

    results: list[TurnFeelResult] = []
    payloads: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        result, payload = run_case(
            base_url=args.base_url.rstrip("/"),
            session_id=args.session_id,
            character_id=args.character_id,
            case_id=str(case.get("id", f"case_{index}")),
            message=str(case["message"]),
            scene_context=case.get("sceneContext", {}),
            poll_seconds=max(args.poll_ms, 20) / 1000.0,
            timeout_seconds=args.timeout_seconds,
        )
        results.append(result)
        payloads.append(payload)
        print_result(result)

    write_csv(csv_path, results)
    json_path.write_text(json.dumps(payloads, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"CSV:  {csv_path}")
    print(f"JSON: {json_path}")

    return 1 if any(result.status != "pass" for result in results) else 0


def load_cases(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return [{"message": message} for message in DEFAULT_CASES]

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("cases file must contain a JSON array")

    cases: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, str):
            cases.append({"message": item})
        elif isinstance(item, dict) and isinstance(item.get("message"), str):
            cases.append(item)
        else:
            raise ValueError("each case must be a string or object with a message field")
    return cases


def run_case(
    *,
    base_url: str,
    session_id: str,
    character_id: str,
    case_id: str,
    message: str,
    scene_context: dict[str, Any],
    poll_seconds: float,
    timeout_seconds: float,
) -> tuple[TurnFeelResult, dict[str, Any]]:
    request_body = {
        "sessionId": session_id,
        "characterId": character_id,
        "message": message,
        "sceneContext": scene_context,
    }

    started = time.perf_counter()
    try:
        accepted = post_json(f"{base_url}/api/runtime/turn/async", request_body)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        elapsed = elapsed_ms(started)
        return make_error(case_id, message, elapsed, f"submit_failed:{exc.__class__.__name__}:{exc}"), {
            "caseId": case_id,
            "error": str(exc),
        }

    accepted_ms = elapsed_ms(started)
    turn_job_id = str(accepted.get("turnJobId", ""))
    if not turn_job_id:
        return make_error(case_id, message, accepted_ms, "missing_turn_job_id"), {
            "caseId": case_id,
            "accepted": accepted,
        }

    first_poll_ms = -1
    response_ready_ms = -1
    tts_ready_ms = -1
    final_payload: dict[str, Any] = {}
    deadline = started + timeout_seconds

    while time.perf_counter() < deadline:
        time.sleep(poll_seconds)
        try:
            payload = get_json(f"{base_url}/api/runtime/turn/jobs/{turn_job_id}")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            total_ms = elapsed_ms(started)
            return make_error(case_id, message, accepted_ms, f"poll_failed:{exc.__class__.__name__}:{exc}"), {
                "caseId": case_id,
                "accepted": accepted,
                "error": str(exc),
            }

        if first_poll_ms < 0:
            first_poll_ms = elapsed_ms(started)
        if response_ready_ms < 0 and payload.get("responseReady"):
            response_ready_ms = elapsed_ms(started)
        if tts_ready_ms < 0 and payload.get("ttsReady"):
            tts_ready_ms = elapsed_ms(started)

        final_payload = payload
        status = str(payload.get("status", ""))
        if status in {"succeeded", "failed"}:
            break

    result = build_result(
        case_id=case_id,
        message=message,
        accepted_ms=accepted_ms,
        first_poll_ms=first_poll_ms,
        response_ready_ms=response_ready_ms,
        tts_ready_ms=tts_ready_ms,
        total_ms=elapsed_ms(started),
        payload=final_payload,
    )
    return result, {"caseId": case_id, "accepted": accepted, "final": final_payload}


def post_json(url: str, body: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def build_result(
    *,
    case_id: str,
    message: str,
    accepted_ms: int,
    first_poll_ms: int,
    response_ready_ms: int,
    tts_ready_ms: int,
    total_ms: int,
    payload: dict[str, Any],
) -> TurnFeelResult:
    response = payload.get("response") or {}
    behavior = response.get("behavior") or {}
    metadata = response.get("metadata") or {}
    speech_timeline = payload.get("speechTimeline") or {}
    visemes = speech_timeline.get("visemes") or []

    issues: list[str] = []
    status = str(payload.get("status", "timeout"))
    if status != "succeeded":
        issues.append(f"status:{status}")
    if metadata.get("fallbackUsed"):
        issues.append("fallback_used")
    if response_ready_ms < 0:
        issues.append("response_not_ready")
    if tts_ready_ms < 0:
        issues.append("tts_not_ready")
    if response_ready_ms > 2200:
        issues.append("response_over_2200ms")
    if tts_ready_ms > 3500:
        issues.append("tts_over_3500ms")

    return TurnFeelResult(
        case_id=case_id,
        status="pass" if not issues else "fail",
        message=message,
        accepted_ms=accepted_ms,
        first_poll_ms=first_poll_ms,
        response_ready_ms=response_ready_ms,
        tts_ready_ms=tts_ready_ms,
        total_ms=total_ms,
        provider=str(metadata.get("provider", "")),
        model=str(metadata.get("model", "")),
        fallback_used=bool(metadata.get("fallbackUsed", False)),
        reply=str(response.get("reply", "")),
        emotion=str(behavior.get("emotion", "")),
        intent=str(behavior.get("intent", "")),
        tts_duration_seconds=float(speech_timeline.get("durationSeconds", -1.0)),
        viseme_count=len(visemes),
        issues=";".join(issues),
    )


def make_error(case_id: str, message: str, elapsed: int, issues: str) -> TurnFeelResult:
    return TurnFeelResult(
        case_id=case_id,
        status="error",
        message=message,
        accepted_ms=elapsed,
        first_poll_ms=-1,
        response_ready_ms=-1,
        tts_ready_ms=-1,
        total_ms=elapsed,
        provider="",
        model="",
        fallback_used=False,
        reply="",
        emotion="",
        intent="",
        tts_duration_seconds=-1.0,
        viseme_count=0,
        issues=issues,
    )


def elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def print_result(result: TurnFeelResult) -> None:
    print(
        f"[{result.status.upper()}] {result.case_id} "
        f"accepted={result.accepted_ms}ms response={result.response_ready_ms}ms "
        f"tts={result.tts_ready_ms}ms total={result.total_ms}ms "
        f"provider={result.provider}/{result.model} fallback={result.fallback_used}"
    )
    print(f"  Q: {result.message}")
    print(f"  A: {result.reply}")
    if result.issues:
        print(f"  issues: {result.issues}")


def write_csv(path: Path, results: list[TurnFeelResult]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(TurnFeelResult.__dataclass_fields__.keys()))
        writer.writeheader()
        for result in results:
            writer.writerow(result.__dict__)


if __name__ == "__main__":
    sys.exit(main())
