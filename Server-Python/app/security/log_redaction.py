import hashlib
import os


def private_log_payloads_enabled() -> bool:
    configured = os.getenv("RUNTIME_LOG_PRIVATE_DATA")
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes", "on"}
    return os.getenv("ENVIRONMENT", "").strip().lower() != "production"


def redact_text(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"[redacted chars={len(value)} sha256={digest}]"


def loggable_text(value: str) -> str:
    if private_log_payloads_enabled():
        return value
    return redact_text(value)
