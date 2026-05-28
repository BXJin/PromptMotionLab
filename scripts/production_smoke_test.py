import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://live3dcharacter-fqfpbcdhawbjggeq.koreacentral-01.azurewebsites.net"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    elapsed_ms: int


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the PromptMotionLab production server.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Production server base URL.")
    parser.add_argument("--timeout", type=float, default=20.0, help="Request timeout seconds.")
    parser.add_argument("--poll-seconds", type=float, default=10.0, help="Async turn polling window.")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    results: list[CheckResult] = []

    health = timed_request("health", "GET", f"{base_url}/health", timeout=args.timeout)
    results.append(health)

    docs = timed_request("docs_disabled", "GET", f"{base_url}/docs", timeout=args.timeout)
    docs.ok = docs.detail.startswith("HTTP 404")
    results.append(docs)

    openapi = timed_request("openapi_disabled", "GET", f"{base_url}/openapi.json", timeout=args.timeout)
    openapi.ok = openapi.detail.startswith("HTTP 404")
    results.append(openapi)

    respond_payload = {
        "sessionId": f"prod_smoke_{int(time.time())}",
        "characterId": "default_girl",
        "message": "hello",
    }
    respond = timed_request(
        "runtime_respond",
        "POST",
        f"{base_url}/api/runtime/respond",
        payload=respond_payload,
        timeout=args.timeout,
    )
    respond.ok = respond.ok and has_json_fields(respond.detail, ["reply", "behavior", "metadata"])
    results.append(respond)

    turn_payload = {
        "sessionId": f"prod_smoke_turn_{int(time.time())}",
        "characterId": "default_girl",
        "message": "hello",
    }
    turn = timed_request(
        "turn_async_submit",
        "POST",
        f"{base_url}/api/runtime/turn/async",
        payload=turn_payload,
        timeout=args.timeout,
    )
    turn_job_id = extract_json_field(turn.detail, "turnJobId")
    turn.ok = turn.ok and isinstance(turn_job_id, str) and bool(turn_job_id)
    results.append(turn)

    if isinstance(turn_job_id, str) and turn_job_id:
        poll = poll_turn_job(base_url, turn_job_id, args.poll_seconds, args.timeout)
        results.append(poll)

    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"{status:4} {result.name:20} {result.elapsed_ms:5}ms {summarize_detail(result.detail)}")

    failed = [result for result in results if not result.ok]
    if failed:
        print(f"\nFailed checks: {', '.join(result.name for result in failed)}", file=sys.stderr)
        return 1

    return 0


def timed_request(
    name: str,
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float,
) -> CheckResult:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=body, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            ok = 200 <= response.status < 300
            return CheckResult(name, ok, text or f"HTTP {response.status}", elapsed_ms)
    except HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return CheckResult(name, False, f"HTTP {exc.code} {text}", elapsed_ms)
    except URLError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return CheckResult(name, False, f"URL error: {exc.reason}", elapsed_ms)
    except TimeoutError:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return CheckResult(name, False, "timeout", elapsed_ms)


def poll_turn_job(base_url: str, turn_job_id: str, poll_seconds: float, timeout: float) -> CheckResult:
    started = time.perf_counter()
    deadline = started + poll_seconds
    last_detail = ""
    while time.perf_counter() < deadline:
        result = timed_request(
            "turn_async_poll",
            "GET",
            f"{base_url}/api/runtime/turn/jobs/{turn_job_id}",
            timeout=timeout,
        )
        last_detail = result.detail
        if result.ok and turn_job_is_ready(result.detail):
            result.elapsed_ms = int((time.perf_counter() - started) * 1000)
            result.ok = True
            return result
        time.sleep(0.5)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return CheckResult("turn_async_poll", False, last_detail or "poll timed out", elapsed_ms)


def turn_job_is_ready(detail: str) -> bool:
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        return False

    status = str(payload.get("status", "")).lower()
    response_ready = bool(payload.get("responseReady") or payload.get("response"))
    tts_ready = bool(payload.get("ttsReady") or payload.get("speechTimeline") or payload.get("segments"))
    failed = status in {"failed", "error"}
    return not failed and response_ready and tts_ready


def has_json_fields(detail: str, fields: list[str]) -> bool:
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        return False
    return all(field in payload for field in fields)


def extract_json_field(detail: str, field: str) -> Any:
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        return None
    return payload.get(field)


def summarize_detail(detail: str) -> str:
    compact = " ".join(detail.split())
    if len(compact) <= 180:
        return compact
    return compact[:177] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
