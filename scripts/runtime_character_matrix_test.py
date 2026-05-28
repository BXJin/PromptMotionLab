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


DEFAULT_CHARACTERS = [
    "default_girl",
    "e_f_n",
    "e_f_s",
    "e_t_n",
    "e_t_s",
    "i_f_n",
    "i_f_s",
    "i_t_n",
    "i_t_s",
]

DEFAULT_CASES_PATH = (
    Path("Docs") / "Plan" / "10-RuntimeCharacter" / "runtime_character_matrix_cases.json"
)


@dataclass(frozen=True)
class MatrixResult:
    character_id: str
    case_id: str
    repeat_index: int
    status: str
    message: str
    accepted_ms: int
    first_poll_ms: int
    response_ready_ms: int
    tts_ready_ms: int
    total_ms: int
    provider: str
    model: str
    route: str
    fallback_used: bool
    reply: str
    emotion: str
    intent: str
    gaze: str
    tts_duration_seconds: float
    viseme_count: int
    segment_count: int
    issues: str


def main() -> int:
    parser = argparse.ArgumentParser(description="PromptMotion character matrix conversation test")
    parser.add_argument("--base-url", default="http://localhost:8010", help="FastAPI server base URL")
    parser.add_argument("--session-prefix", default="matrix_test", help="session id prefix")
    parser.add_argument("--characters", default=",".join(DEFAULT_CHARACTERS), help="comma-separated character ids")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH, help="JSON test case file")
    parser.add_argument("--repeats", type=int, default=2, help="runs per character/case")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("Build") / "reports" / "runtime_character_matrix",
        help="output directory",
    )
    parser.add_argument("--poll-ms", type=int, default=100, help="job polling interval in milliseconds")
    parser.add_argument("--poll-retries", type=int, default=1, help="retries for transient poll HTTP errors")
    parser.add_argument("--timeout-seconds", type=float, default=30.0, help="per turn timeout")
    args = parser.parse_args()

    characters = [item.strip() for item in args.characters.split(",") if item.strip()]
    cases = load_cases(args.cases)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = args.out_dir / f"runtime_character_matrix_{timestamp}.csv"
    json_path = args.out_dir / f"runtime_character_matrix_{timestamp}.json"
    summary_path = args.out_dir / f"runtime_character_matrix_{timestamp}_summary.json"

    results: list[MatrixResult] = []
    payloads: list[dict[str, Any]] = []

    for character_id in characters:
        for case in cases:
            for repeat_index in range(1, max(1, args.repeats) + 1):
                result, payload = run_case(
                    base_url=args.base_url.rstrip("/"),
                    session_id=f"{args.session_prefix}_{timestamp}_{character_id}_{case['id']}_{repeat_index}",
                    character_id=character_id,
                    case=case,
                    repeat_index=repeat_index,
                    poll_seconds=max(args.poll_ms, 20) / 1000.0,
                    poll_retries=max(0, args.poll_retries),
                    timeout_seconds=args.timeout_seconds,
                )
                results.append(result)
                payloads.append(payload)
                print_result(result)

    write_csv(csv_path, results)
    json_path.write_text(json.dumps(payloads, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = build_summary(results)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"CSV:     {csv_path}")
    print(f"JSON:    {json_path}")
    print(f"Summary: {summary_path}")

    return 1 if any(result.status != "pass" for result in results) else 0


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("cases file must contain a JSON array")

    cases: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict) or not isinstance(item.get("message"), str):
            raise ValueError("each case must be an object with a message field")
        case = dict(item)
        case["id"] = str(case.get("id") or f"case_{index}")
        cases.append(case)
    return cases


def run_case(
    *,
    base_url: str,
    session_id: str,
    character_id: str,
    case: dict[str, Any],
    repeat_index: int,
    poll_seconds: float,
    poll_retries: int,
    timeout_seconds: float,
) -> tuple[MatrixResult, dict[str, Any]]:
    message = str(case["message"])
    request_body = {
        "sessionId": session_id,
        "characterId": character_id,
        "message": message,
        "sceneContext": case.get("sceneContext", {}),
    }

    started = time.perf_counter()
    try:
        accepted = post_json(f"{base_url}/api/runtime/turn/async", request_body)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        elapsed = elapsed_ms(started)
        return make_error(character_id, case["id"], repeat_index, message, elapsed, f"submit_failed:{exc}"), {
            "characterId": character_id,
            "case": case,
            "error": str(exc),
        }

    accepted_ms = elapsed_ms(started)
    turn_job_id = str(accepted.get("turnJobId", ""))
    if not turn_job_id:
        return make_error(character_id, case["id"], repeat_index, message, accepted_ms, "missing_turn_job_id"), {
            "characterId": character_id,
            "case": case,
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
            payload = get_json_with_retries(
                f"{base_url}/api/runtime/turn/jobs/{turn_job_id}",
                retries=poll_retries,
                delay_seconds=max(0.05, poll_seconds),
            )
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            elapsed = elapsed_ms(started)
            return make_error(character_id, case["id"], repeat_index, message, elapsed, f"poll_failed:{exc}"), {
                "characterId": character_id,
                "case": case,
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
        if str(payload.get("status", "")) in {"succeeded", "failed"}:
            break

    result = build_result(
        character_id=character_id,
        case=case,
        repeat_index=repeat_index,
        message=message,
        accepted_ms=accepted_ms,
        first_poll_ms=first_poll_ms,
        response_ready_ms=response_ready_ms,
        tts_ready_ms=tts_ready_ms,
        total_ms=elapsed_ms(started),
        payload=final_payload,
    )
    return result, {
        "characterId": character_id,
        "case": case,
        "repeatIndex": repeat_index,
        "accepted": accepted,
        "final": final_payload,
    }


def post_json(url: str, body: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json_with_retries(url: str, *, retries: int, delay_seconds: float) -> dict[str, Any]:
    last_exc: HTTPError | URLError | TimeoutError | OSError | None = None
    for attempt in range(retries + 1):
        try:
            return get_json(url)
        except HTTPError as exc:
            last_exc = exc
            if exc.code != 404 or attempt >= retries:
                raise
            time.sleep(delay_seconds)
        except (URLError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt >= retries:
                raise
            time.sleep(delay_seconds)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("poll retry failed without an exception")


def build_result(
    *,
    character_id: str,
    case: dict[str, Any],
    repeat_index: int,
    message: str,
    accepted_ms: int,
    first_poll_ms: int,
    response_ready_ms: int,
    tts_ready_ms: int,
    total_ms: int,
    payload: dict[str, Any],
) -> MatrixResult:
    response = payload.get("response") or {}
    behavior = response.get("behavior") or {}
    metadata = response.get("metadata") or {}
    speech_timeline = payload.get("speechTimeline") or {}
    visemes = speech_timeline.get("visemes") or []
    segments = speech_timeline.get("segments") or []

    issues = evaluate_case(character_id, case, payload, response_ready_ms, tts_ready_ms)
    return MatrixResult(
        character_id=character_id,
        case_id=str(case["id"]),
        repeat_index=repeat_index,
        status="pass" if not issues else "fail",
        message=message,
        accepted_ms=accepted_ms,
        first_poll_ms=first_poll_ms,
        response_ready_ms=response_ready_ms,
        tts_ready_ms=tts_ready_ms,
        total_ms=total_ms,
        provider=str(metadata.get("provider", "")),
        model=str(metadata.get("model", "")),
        route=str(metadata.get("route", "")),
        fallback_used=bool(metadata.get("fallbackUsed", False)),
        reply=str(response.get("reply", "")),
        emotion=str(behavior.get("emotion", "")),
        intent=str(behavior.get("intent", "")),
        gaze=str(behavior.get("gaze", "")),
        tts_duration_seconds=float(speech_timeline.get("durationSeconds", -1.0)),
        viseme_count=len(visemes),
        segment_count=len(segments),
        issues=";".join(issues),
    )


def evaluate_case(
    character_id: str,
    case: dict[str, Any],
    payload: dict[str, Any],
    response_ready_ms: int,
    tts_ready_ms: int,
) -> list[str]:
    response = payload.get("response") or {}
    behavior = response.get("behavior") or {}
    metadata = response.get("metadata") or {}
    issues: list[str] = []

    if str(payload.get("status", "")) != "succeeded":
        issues.append(f"status:{payload.get('status', 'missing')}")
    if metadata.get("fallbackUsed"):
        issues.append("fallback_used")
    if not response.get("reply"):
        issues.append("empty_reply")
    if response_ready_ms < 0:
        issues.append("response_not_ready")
    if tts_ready_ms < 0:
        issues.append("tts_not_ready")

    expected_model_contains = case.get("expectedModelContains")
    if expected_model_contains and expected_model_contains not in str(metadata.get("model", "")):
        issues.append(f"model_expected_contains:{expected_model_contains}:actual:{metadata.get('model')}")

    expected_route = case.get("expectedRoute")
    if expected_route and metadata.get("route") != expected_route:
        issues.append(f"route_expected:{expected_route}:actual:{metadata.get('route')}")

    expected_emotion_any = case.get("expectedEmotionAny")
    character_expected = case.get("expectedEmotionByCharacter") or {}
    expected_for_character = character_expected.get(character_id, expected_emotion_any)
    if expected_for_character and behavior.get("emotion") not in expected_for_character:
        issues.append(f"emotion_not_in:{expected_for_character}:actual:{behavior.get('emotion')}")

    expected_intent_any = case.get("expectedIntentAny")
    if expected_intent_any and behavior.get("intent") not in expected_intent_any:
        issues.append(f"intent_not_in:{expected_intent_any}:actual:{behavior.get('intent')}")

    expected_gaze = case.get("expectedGaze")
    if expected_gaze and behavior.get("gaze") != expected_gaze:
        issues.append(f"gaze_expected:{expected_gaze}:actual:{behavior.get('gaze')}")

    return issues


def make_error(
    character_id: str,
    case_id: str,
    repeat_index: int,
    message: str,
    elapsed: int,
    issues: str,
) -> MatrixResult:
    return MatrixResult(
        character_id=character_id,
        case_id=case_id,
        repeat_index=repeat_index,
        status="error",
        message=message,
        accepted_ms=elapsed,
        first_poll_ms=-1,
        response_ready_ms=-1,
        tts_ready_ms=-1,
        total_ms=elapsed,
        provider="",
        model="",
        route="",
        fallback_used=False,
        reply="",
        emotion="",
        intent="",
        gaze="",
        tts_duration_seconds=-1.0,
        viseme_count=0,
        segment_count=0,
        issues=issues,
    )


def elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def print_result(result: MatrixResult) -> None:
    print(
        f"[{result.status.upper()}] {result.character_id}/{result.case_id}/r{result.repeat_index} "
        f"model={result.model} route={result.route} response={result.response_ready_ms}ms "
        f"tts={result.tts_ready_ms}ms total={result.total_ms}ms"
    )
    print(f"  A: {result.reply}")
    if result.issues:
        print(f"  issues: {result.issues}")


def write_csv(path: Path, results: list[MatrixResult]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(MatrixResult.__dataclass_fields__.keys()))
        writer.writeheader()
        for result in results:
            writer.writerow(result.__dict__)


def build_summary(results: list[MatrixResult]) -> dict[str, Any]:
    by_model: dict[str, list[MatrixResult]] = {}
    by_character: dict[str, list[MatrixResult]] = {}
    by_route: dict[str, list[MatrixResult]] = {}
    for result in results:
        by_model.setdefault(result.model or "unknown", []).append(result)
        by_character.setdefault(result.character_id, []).append(result)
        by_route.setdefault(result.route or "unknown", []).append(result)

    return {
        "total": len(results),
        "passed": sum(1 for result in results if result.status == "pass"),
        "failed": sum(1 for result in results if result.status != "pass"),
        "byModel": {model: summarize_group(items) for model, items in by_model.items()},
        "byRoute": {route: summarize_group(items) for route, items in by_route.items()},
        "byCharacter": {character: summarize_group(items) for character, items in by_character.items()},
    }


def summarize_group(items: list[MatrixResult]) -> dict[str, Any]:
    response_values = [item.response_ready_ms for item in items if item.response_ready_ms >= 0]
    tts_values = [item.tts_ready_ms for item in items if item.tts_ready_ms >= 0]
    return {
        "count": len(items),
        "passed": sum(1 for item in items if item.status == "pass"),
        "fallbacks": sum(1 for item in items if item.fallback_used),
        "failed": sum(1 for item in items if item.status != "pass"),
        "avgResponseReadyMs": average(response_values),
        "p95ResponseReadyMs": percentile(response_values, 95),
        "maxResponseReadyMs": max(response_values, default=-1),
        "avgTtsReadyMs": average(tts_values),
        "p95TtsReadyMs": percentile(tts_values, 95),
        "maxTtsReadyMs": max(tts_values, default=-1),
    }


def average(values: list[int]) -> int:
    if not values:
        return -1
    return int(sum(values) / len(values))


def percentile(values: list[int], percentile_value: int) -> int:
    if not values:
        return -1
    sorted_values = sorted(values)
    index = int((len(sorted_values) - 1) * percentile_value / 100)
    return sorted_values[index]


if __name__ == "__main__":
    sys.exit(main())
