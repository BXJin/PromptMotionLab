from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_CASES = [
    {
        "id": "greeting_ko",
        "message": "안녕",
        "expected_intent": "greet",
        "expected_emotion_any": ["friendly", "happy"],
        "expected_provider": "FastPathRuntimeProvider",
    },
    {
        "id": "science_uncertain_ko",
        "message": "양자역학이 의식에 영향을 준다는 게 사실이야?",
        "expected_intent_any": ["answer", "clarify"],
        "expected_emotion_any": ["thinking", "curious", "uncertain", "concerned"],
    },
    {
        "id": "emotional_support_ko",
        "message": "나 요즘 너무 힘들고 아무것도 하기 싫어",
        "expected_intent_any": ["clarify", "answer"],
        "expected_emotion_any": ["concerned", "apologetic", "uncertain"],
    },
    {
        "id": "object_explain_ko",
        "message": "이 전시물 설명해줘",
        "sceneContext": {
            "locationId": "demo_hall",
            "focusedObjectId": "exhibit_01",
            "nearbyObjectIds": ["exhibit_01"],
            "interactionMode": "object_selected",
        },
        "expected_intent": "explain",
        "expected_gaze": "focused_object",
    },
    {
        "id": "unknown_ko",
        "message": "확실하지 않으면 모른다고 말해줘. 이 유물의 제작자는 누구야?",
        "sceneContext": {
            "focusedObjectId": "unknown_artifact",
            "interactionMode": "object_selected",
        },
        "expected_emotion_any": ["uncertain", "thinking", "concerned"],
    },
]


@dataclass(frozen=True)
class SmokeResult:
    case_id: str
    status: str
    message: str
    reply: str
    emotion: str
    intent: str
    gaze: str
    gesture_key: str
    provider: str
    model: str
    fallback_used: bool
    server_ms: int
    client_ms: int
    request_id: str
    issues: str


def main() -> int:
    parser = argparse.ArgumentParser(description="PromptMotion runtime LLM smoke test")
    parser.add_argument("--base-url", default="http://localhost:8010", help="FastAPI server base URL")
    parser.add_argument("--session-id", default="llm_smoke_test", help="runtime session id")
    parser.add_argument("--character-id", default="default_girl", help="runtime character id")
    parser.add_argument("--cases", type=Path, help="optional JSON file with test cases")
    parser.add_argument("--out-dir", type=Path, default=Path("Build") / "reports", help="output directory")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = args.out_dir / f"runtime_llm_smoke_{timestamp}.csv"
    json_path = args.out_dir / f"runtime_llm_smoke_{timestamp}.json"

    results: list[SmokeResult] = []
    raw_payloads: list[dict[str, Any]] = []

    for case in cases:
        result, raw = run_case(
            base_url=args.base_url.rstrip("/"),
            session_id=args.session_id,
            character_id=args.character_id,
            case=case,
        )
        results.append(result)
        raw_payloads.append(raw)
        print_result(result)

    write_csv(csv_path, results)
    json_path.write_text(
        json.dumps(raw_payloads, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"CSV:  {csv_path}")
    print(f"JSON: {json_path}")

    failed = [result for result in results if result.status != "pass"]
    return 1 if failed else 0


def load_cases(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return DEFAULT_CASES

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("cases file must contain a JSON array")
    return data


def run_case(
    base_url: str,
    session_id: str,
    character_id: str,
    case: dict[str, Any],
) -> tuple[SmokeResult, dict[str, Any]]:
    message = str(case["message"])
    request_body = {
        "sessionId": session_id,
        "characterId": character_id,
        "message": message,
        "sceneContext": case.get("sceneContext", {}),
    }

    started = time.perf_counter()
    try:
        payload = post_json(f"{base_url}/api/runtime/respond", request_body)
        client_ms = int((time.perf_counter() - started) * 1000)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        client_ms = int((time.perf_counter() - started) * 1000)
        result = SmokeResult(
            case_id=str(case.get("id", "unknown")),
            status="error",
            message=message,
            reply="",
            emotion="",
            intent="",
            gaze="",
            gesture_key="",
            provider="",
            model="",
            fallback_used=False,
            server_ms=-1,
            client_ms=client_ms,
            request_id="",
            issues=f"request_failed:{exc.__class__.__name__}:{exc}",
        )
        return result, {"case": case, "error": result.issues}

    behavior = payload.get("behavior") or {}
    metadata = payload.get("metadata") or {}
    issues = evaluate(case, payload)
    result = SmokeResult(
        case_id=str(case.get("id", "unknown")),
        status="pass" if not issues else "fail",
        message=message,
        reply=str(payload.get("reply", "")),
        emotion=str(behavior.get("emotion", "")),
        intent=str(behavior.get("intent", "")),
        gaze=str(behavior.get("gaze", "")),
        gesture_key=str(behavior.get("gestureKey", "")),
        provider=str(metadata.get("provider", "")),
        model=str(metadata.get("model", "")),
        fallback_used=bool(metadata.get("fallbackUsed", False)),
        server_ms=int(metadata.get("totalServerMs", -1)),
        client_ms=client_ms,
        request_id=str(metadata.get("requestId", "")),
        issues=";".join(issues),
    )
    return result, {"case": case, "response": payload, "clientMs": client_ms, "issues": issues}


def post_json(url: str, body: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def evaluate(case: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    behavior = payload.get("behavior") or {}
    metadata = payload.get("metadata") or {}

    if metadata.get("fallbackUsed"):
        issues.append("fallback_used")

    expected_intent = case.get("expected_intent")
    if expected_intent and behavior.get("intent") != expected_intent:
        issues.append(f"intent_expected:{expected_intent}:actual:{behavior.get('intent')}")

    expected_intent_any = case.get("expected_intent_any")
    if expected_intent_any and behavior.get("intent") not in expected_intent_any:
        issues.append(f"intent_not_in:{expected_intent_any}:actual:{behavior.get('intent')}")

    expected_emotion = case.get("expected_emotion")
    if expected_emotion and behavior.get("emotion") != expected_emotion:
        issues.append(f"emotion_expected:{expected_emotion}:actual:{behavior.get('emotion')}")

    expected_emotion_any = case.get("expected_emotion_any")
    if expected_emotion_any and behavior.get("emotion") not in expected_emotion_any:
        issues.append(f"emotion_not_in:{expected_emotion_any}:actual:{behavior.get('emotion')}")

    expected_gaze = case.get("expected_gaze")
    if expected_gaze and behavior.get("gaze") != expected_gaze:
        issues.append(f"gaze_expected:{expected_gaze}:actual:{behavior.get('gaze')}")

    expected_provider = case.get("expected_provider")
    if expected_provider and metadata.get("provider") != expected_provider:
        issues.append(f"provider_expected:{expected_provider}:actual:{metadata.get('provider')}")

    if not payload.get("reply"):
        issues.append("empty_reply")

    return issues


def print_result(result: SmokeResult) -> None:
    print(
        f"[{result.status.upper()}] {result.case_id} "
        f"provider={result.provider}/{result.model} fallback={result.fallback_used} "
        f"server={result.server_ms}ms client={result.client_ms}ms "
        f"emotion={result.emotion} intent={result.intent}"
    )
    print(f"  Q: {result.message}")
    print(f"  A: {result.reply}")
    if result.issues:
        print(f"  issues: {result.issues}")


def write_csv(path: Path, results: list[SmokeResult]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(SmokeResult.__dataclass_fields__.keys()))
        writer.writeheader()
        for result in results:
            writer.writerow(result.__dict__)


if __name__ == "__main__":
    sys.exit(main())
