from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.security import loggable_text

logger = logging.getLogger(__name__)


class ProviderFailureLogger:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()

    @classmethod
    def default(cls) -> "ProviderFailureLogger":
        configured_path = os.getenv("RUNTIME_PROVIDER_FAILURE_LOG_PATH")
        if configured_path:
            return cls(Path(configured_path))

        server_root = Path(__file__).resolve().parents[2]
        return cls(server_root / "data" / "metrics" / "runtime_provider_failures.jsonl")

    def append(
        self,
        *,
        provider: str,
        model: str,
        error_type: str,
        error_message: str,
        sample: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "model": model,
            "errorType": error_type,
            "errorMessage": error_message,
            "sample": loggable_text(sample)[:1000],
            "metadata": metadata or {},
        }

        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                with self._path.open("a", encoding="utf-8") as file:
                    file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
                    file.write("\n")
        except OSError as exc:
            logger.warning("Failed to append provider failure log. path=%s error=%s", self._path, exc)
