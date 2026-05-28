import csv
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from app.contracts.responses import RuntimeResponseMetadata
from app.contracts.runtime_behavior import BehaviorJson

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeLatencyMetric:
    metadata: RuntimeResponseMetadata
    session_id: str
    message_length: int
    emotion: str
    intent: str
    stt_ms: int = -1
    tts_ms: int = -1
    unreal_round_trip_ms: int = -1
    first_visible_reaction_ms: int = -1
    first_audio_start_ms: int = -1
    notes: str = ""


class LatencyMetricsLogger:
    PreviousHeaderWithoutRoute = [
        "timestamp",
        "session_id",
        "request_id",
        "input_mode",
        "message_length",
        "provider",
        "model",
        "tech_profile",
        "fallback_used",
        "stt_ms",
        "llm_ms",
        "tts_ms",
        "total_server_ms",
        "unreal_round_trip_ms",
        "first_visible_reaction_ms",
        "first_audio_start_ms",
        "emotion",
        "intent",
        "notes",
    ]
    Header = [
        "timestamp",
        "session_id",
        "request_id",
        "input_mode",
        "message_length",
        "provider",
        "model",
        "route",
        "tech_profile",
        "fallback_used",
        "stt_ms",
        "llm_ms",
        "tts_ms",
        "total_server_ms",
        "unreal_round_trip_ms",
        "first_visible_reaction_ms",
        "first_audio_start_ms",
        "emotion",
        "intent",
        "notes",
    ]

    def __init__(self, csv_path: Path) -> None:
        self._csv_path = csv_path
        self._lock = Lock()

    @classmethod
    def default(cls) -> "LatencyMetricsLogger":
        configured_path = os.getenv("RUNTIME_METRICS_CSV_PATH")
        if configured_path:
            return cls(Path(configured_path))

        server_root = Path(__file__).resolve().parents[2]
        return cls(server_root / "data" / "metrics" / "runtime_latency.csv")

    def append_runtime_response(
        self,
        metadata: RuntimeResponseMetadata,
        session_id: str,
        message: str,
        behavior: BehaviorJson,
        notes: str = "",
    ) -> None:
        self.append(
            RuntimeLatencyMetric(
                metadata=metadata,
                session_id=session_id,
                message_length=len(message),
                emotion=str(behavior.emotion),
                intent=str(behavior.intent),
                notes=notes,
            )
        )

    def append(self, metric: RuntimeLatencyMetric) -> None:
        try:
            self._csv_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                self._migrate_legacy_header_locked()
                should_write_header = not self._csv_path.exists() or self._csv_path.stat().st_size == 0
                with self._csv_path.open("a", newline="", encoding="utf-8-sig") as file:
                    writer = csv.DictWriter(file, fieldnames=self.Header)
                    if should_write_header:
                        writer.writeheader()
                    writer.writerow(self._to_row(metric))
        except OSError as exc:
            logger.warning("Failed to append latency metrics csv. path=%s error=%s", self._csv_path, exc)

    def _migrate_legacy_header_locked(self) -> None:
        if not self._csv_path.exists() or self._csv_path.stat().st_size == 0:
            return

        with self._csv_path.open("r", newline="", encoding="utf-8-sig") as file:
            rows = list(csv.reader(file))
        if not rows:
            return
        if rows[0] == self.Header:
            return
        if rows[0] != self.PreviousHeaderWithoutRoute:
            logger.warning("Latency metrics csv has an unknown header. path=%s", self._csv_path)
            return

        route_index = self.Header.index("route")
        migrated_rows = [self.Header]
        for row in rows[1:]:
            if len(row) == len(self.Header):
                migrated_rows.append(row)
                continue
            migrated = list(row)
            migrated.insert(route_index, "")
            if len(migrated) > len(self.Header):
                migrated = migrated[: len(self.Header) - 1] + [";".join(migrated[len(self.Header) - 1 :])]
            migrated_rows.append(migrated)

        with self._csv_path.open("w", newline="", encoding="utf-8-sig") as file:
            csv.writer(file).writerows(migrated_rows)

    def _to_row(self, metric: RuntimeLatencyMetric) -> dict[str, object]:
        metadata = metric.metadata
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": metric.session_id,
            "request_id": metadata.request_id,
            "input_mode": metadata.input_mode,
            "message_length": metric.message_length,
            "provider": metadata.provider,
            "model": metadata.model,
            "route": metadata.route or "",
            "tech_profile": metadata.tech_profile,
            "fallback_used": metadata.fallback_used,
            "stt_ms": metric.stt_ms,
            "llm_ms": metadata.provider_latency_ms,
            "tts_ms": metric.tts_ms,
            "total_server_ms": metadata.total_server_ms,
            "unreal_round_trip_ms": metric.unreal_round_trip_ms,
            "first_visible_reaction_ms": metric.first_visible_reaction_ms,
            "first_audio_start_ms": metric.first_audio_start_ms,
            "emotion": metric.emotion,
            "intent": metric.intent,
            "notes": metric.notes,
        }
