from __future__ import annotations

import argparse
import ast
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


DATASET_NAME = "NLPBada/korean-persona-chat-dataset"
DEFAULT_PROFILES = ("airi", "airi_direct", "airi_soft", "airi_practical")

GENERIC_ASSISTANT_PHRASES = (
    "언제든 말해",
    "언제든 이야기",
    "도움이 필요하면",
    "필요하면 언제든",
    "더 필요하면",
    "편하게 말",
)

PERSONA_LOCK_PHRASES = (
    "나는 ",
    "내 직업",
    "우리 가족",
    "우리 엄마",
    "우리 아빠",
    "내 나이",
    "살이야",
    "살이고",
    "서울 살아",
    "부산 살아",
    "대구 살아",
)

EMOTIONAL_HINTS = (
    "힘들",
    "슬프",
    "외롭",
    "피곤",
    "지쳤",
    "걱정",
    "불안",
    "괜찮",
)

TASK_HINTS = (
    "해야",
    "방법",
    "어떻게",
    "추천",
    "정리",
    "문제",
    "실패",
    "다음",
    "준비",
)


@dataclass(frozen=True)
class Pair:
    source_split: str
    source_id: str
    turn_index: int
    user_message: str
    assistant_reply: str
    persona: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Airi style candidates from Korean PersonaChat.")
    parser.add_argument("--dataset", default=DATASET_NAME)
    parser.add_argument("--split", default="train", help="dataset split to read")
    parser.add_argument("--limit", type=int, default=300, help="max source rows to scan")
    parser.add_argument("--max-per-profile", type=int, default=120)
    parser.add_argument("--profiles", nargs="*", default=list(DEFAULT_PROFILES))
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("Build") / "reports" / "airi_style_candidates",
    )
    args = parser.parse_args()

    dataset = load_hf_dataset(args.dataset, args.split)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    counts = {profile: 0 for profile in args.profiles}
    for pair in iter_pairs(dataset, split=args.split, limit=args.limit):
        base_reason = reject_reason(pair)
        if base_reason:
            continue

        for profile in args.profiles:
            if counts.get(profile, 0) >= args.max_per_profile:
                continue

            profile_reason = profile_reject_reason(profile, pair)
            if profile_reason:
                continue

            rows.append(
                {
                    "source_dataset": args.dataset,
                    "source_split": pair.source_split,
                    "source_id": pair.source_id,
                    "turn_index": pair.turn_index,
                    "target_profile": profile,
                    "user_message": pair.user_message,
                    "source_reply": pair.assistant_reply,
                    "custom_reply": customize_reply(profile, pair.assistant_reply),
                    "persona": pair.persona,
                    "auto_reason": profile_reason or "candidate",
                    "keep_label": "",
                    "rewrite_reply": "",
                    "notes": "",
                }
            )
            counts[profile] += 1

        if all(counts.get(profile, 0) >= args.max_per_profile for profile in args.profiles):
            break

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = args.out_dir / f"airi_persona_chat_candidates_{timestamp}.csv"
    summary_path = args.out_dir / f"airi_persona_chat_candidates_{timestamp}_summary.json"
    write_csv(csv_path, rows)
    summary_path.write_text(
        json.dumps({"rows": len(rows), "counts": counts}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"CSV={csv_path}")
    print(f"SUMMARY={summary_path}")
    print(json.dumps({"rows": len(rows), "counts": counts}, ensure_ascii=False, indent=2))
    return 0


def load_hf_dataset(dataset_name: str, split: str) -> Any:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: datasets. Install it with `pip install datasets` before running this script."
        ) from exc
    return load_dataset(dataset_name, split=split)


def iter_pairs(dataset: Any, *, split: str, limit: int) -> Iterable[Pair]:
    for row_index, row in enumerate(dataset):
        if row_index >= limit:
            break

        dialog = parse_dialog(row.get("session_dialog"))
        persona = normalize_text(row.get("session_persona", ""))
        if len(dialog) < 2:
            continue

        for turn_index in range(len(dialog) - 1):
            user_message = normalize_text(dialog[turn_index])
            assistant_reply = normalize_text(dialog[turn_index + 1])
            if not user_message or not assistant_reply:
                continue
            yield Pair(
                source_split=split,
                source_id=str(row.get("id", row_index)),
                turn_index=turn_index,
                user_message=user_message,
                assistant_reply=assistant_reply,
                persona=persona,
            )


def parse_dialog(value: Any) -> list[str]:
    if isinstance(value, list):
        return [normalize_dialog_item(item) for item in value]
    if not isinstance(value, str):
        return []

    text = value.strip()
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(text)
        except Exception:
            continue
        if isinstance(parsed, list):
            return [normalize_dialog_item(item) for item in parsed]

    return [normalize_text(line) for line in re.split(r"\n+|<\|endoftext\|>", text) if normalize_text(line)]


def normalize_dialog_item(item: Any) -> str:
    if isinstance(item, str):
        return normalize_text(item)
    if isinstance(item, dict):
        for key in ("text", "utterance", "content", "message", "value"):
            value = item.get(key)
            if isinstance(value, str):
                return normalize_text(value)
    return normalize_text(str(item))


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def reject_reason(pair: Pair) -> str:
    reply = pair.assistant_reply
    if len(reply) < 4:
        return "too_short"
    if len(reply) > 80:
        return "too_long"
    if reply.count("?") > 2:
        return "too_many_questions"
    if any(phrase in reply for phrase in GENERIC_ASSISTANT_PHRASES):
        return "generic_assistant_phrase"
    if any(phrase in reply for phrase in PERSONA_LOCK_PHRASES):
        return "persona_locked_reply"
    if has_no_korean(reply):
        return "not_korean"
    return ""


def profile_reject_reason(profile: str, pair: Pair) -> str:
    reply = pair.assistant_reply
    user_message = pair.user_message
    is_emotional = any(hint in user_message or hint in reply for hint in EMOTIONAL_HINTS)
    is_task = any(hint in user_message for hint in TASK_HINTS)

    if profile == "airi_soft" and not is_emotional:
        return "soft_requires_emotional_context"
    if profile == "airi_practical" and not is_task:
        return "practical_requires_task_context"
    if profile == "airi_direct" and len(reply) > 55:
        return "direct_too_long"
    return ""


def customize_reply(profile: str, reply: str) -> str:
    text = normalize_text(reply)
    text = remove_generic_tail(text)

    if profile in {"airi_direct", "airi_practical"}:
        text = strip_laughter(text)
        text = keep_sentences(text, max_sentences=1)
    elif profile == "airi_soft":
        text = keep_sentences(text, max_sentences=2)
    else:
        text = keep_sentences(text, max_sentences=2)

    return text


def remove_generic_tail(text: str) -> str:
    for phrase in GENERIC_ASSISTANT_PHRASES:
        index = text.find(phrase)
        if index >= 0:
            return text[:index].rstrip(" ,.!?")
    return text


def strip_laughter(text: str) -> str:
    return re.sub(r"[ㅋㅎ]{2,}|하하+|히히+", "", text).strip()


def keep_sentences(text: str, *, max_sentences: int) -> str:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if not parts:
        return text
    return " ".join(parts[:max_sentences])


def has_no_korean(text: str) -> bool:
    return not any("가" <= character <= "힣" for character in text)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "source_dataset",
        "source_split",
        "source_id",
        "turn_index",
        "target_profile",
        "user_message",
        "source_reply",
        "custom_reply",
        "persona",
        "auto_reason",
        "keep_label",
        "rewrite_reply",
        "notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
