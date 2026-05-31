from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


DATA_DIR = Path("Docs") / "Plan" / "10-RuntimeCharacter" / "data" / "jsonl"
DEFAULT_OUT_DIR = Path("Build") / "reports" / "airi_style_candidates"

ALIASES = {
    "e_f_n": "airi_bright",
    "e_f_s": "airi_cheerful",
    "e_t_n": "airi_idea",
    "e_t_s": "airi_direct",
    "i_f_n": "airi_soft",
    "i_f_s": "airi_calm",
    "i_t_n": "airi_reflective",
    "i_t_s": "airi_practical",
}

OPPOSITE_ENERGY_ALIAS = {
    "e_f_n": "i_f_n",
    "e_f_s": "i_f_s",
    "e_t_n": "i_t_n",
    "e_t_s": "i_t_s",
    "i_f_n": "e_f_n",
    "i_f_s": "e_f_s",
    "i_t_n": "e_t_n",
    "i_t_s": "e_t_s",
}

PROFILE_LABELS = {
    "e_f_n": "bright",
    "e_f_s": "cheerful",
    "e_t_n": "idea",
    "e_t_s": "direct",
    "i_f_n": "soft",
    "i_f_s": "calm",
    "i_t_n": "reflective",
    "i_t_s": "practical",
}

HARD_REJECT_PATTERNS = (
    r"^안녕",
    r"^나는\s",
    r"^나도\s.*(없어|좋아|싫어|살아|전공|직업|남자|여자)",
    r"\d+대\s*(남자|여자)",
    r"(고양|스위스|무역학과|서기관)",
    r"(선생님|학생|반려자)",
    r"(부모님|남편|아내|아들|딸)",
)

GENERIC_BAD_PHRASES = (
    "도움이 필요하면",
    "언제든",
    "말씀해 주세요",
    "무엇을 도와",
)

TOPIC_KEYWORDS = {
    "food": ("먹", "맛있", "음식", "카페", "커피", "과일", "복숭아"),
    "movie": ("영화", "드라마", "멜로", "넷플"),
    "music": ("음악", "노래", "힙합", "가수"),
    "travel": ("여행", "바다", "산", "스위스", "떠나"),
    "sport": ("운동", "농구", "수영", "스쿼시", "테니스"),
    "work": ("회사", "이직", "직업", "준비", "면접", "커리어", "프로젝트"),
    "game": ("게임", "롤", "챔피언", "플레이"),
}

CATEGORY_KEYWORDS = {
    "comfort": ("힘들", "슬프", "외로", "우울", "걱정", "불안", "지쳤", "피곤", "속상", "괜찮"),
    "thanks": ("고마", "감사"),
    "decision": ("해야", "고민", "어떡", "어떻게", "결정", "선택", "기준"),
    "encourage": ("해봐", "하자", "좋아", "괜찮", "멋있", "재밌"),
}


@dataclass(frozen=True)
class SourceCandidate:
    source_split: str
    source_id: str
    source_index: int
    source_utterance: str
    topic: str
    category: str
    score: int


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mine source-utterance-first Airi candidates from Korean PersonaChat JSONL."
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max-per-alias", type=int, default=50)
    parser.add_argument("--splits", nargs="*", default=["train", "validation"])
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    candidates = sorted(iter_source_candidates(args.splits), key=lambda item: item.score, reverse=True)
    rows = build_rows(candidates, max_per_alias=args.max_per_alias)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = args.out_dir / f"airi_source_utterance_candidates_{timestamp}.csv"
    summary_path = args.out_dir / f"airi_source_utterance_candidates_{timestamp}_summary.json"

    write_csv(csv_path, rows)
    counts = Counter(row["mbti_alias"] for row in rows)
    unique_replies = {
        alias: len({row["airi_reply"] for row in rows if row["mbti_alias"] == alias}) for alias in ALIASES
    }
    summary = {
        "rows": len(rows),
        "counts": dict(sorted(counts.items())),
        "unique_replies": unique_replies,
        "source": "Docs/Plan/10-RuntimeCharacter/data/jsonl",
        "method": "source_utterance_first",
        "note": "source_utterance is the mined answer candidate; airi_reply is minimally polished from it.",
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"CSV={csv_path}")
    print(f"SUMMARY={summary_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def iter_source_candidates(splits: Iterable[str]) -> Iterable[SourceCandidate]:
    seen: set[str] = set()
    for split in splits:
        path = DATA_DIR / f"korean_persona_chat_{split}.jsonl"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                source_id = str(row.get("id", ""))
                for index, utterance in enumerate(row.get("session_dialog", [])):
                    text = clean_text(str(utterance))
                    if text in seen:
                        continue
                    if reject_source_utterance(text):
                        continue
                    topic = infer_topic(text)
                    category = infer_category(text)
                    score = score_candidate(text, topic, category)
                    if score < 4:
                        continue
                    seen.add(text)
                    yield SourceCandidate(
                        source_split=split,
                        source_id=source_id,
                        source_index=index,
                        source_utterance=text,
                        topic=topic,
                        category=category,
                        score=score,
                    )


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().strip("\"' ")


def reject_source_utterance(text: str) -> bool:
    if len(text) < 5 or len(text) > 72:
        return True
    if not re.search(r"[가-힣]", text):
        return True
    if any(phrase in text for phrase in GENERIC_BAD_PHRASES):
        return True
    if any(re.search(pattern, text) for pattern in HARD_REJECT_PATTERNS):
        return True
    if text.count("?") > 2:
        return True
    if text.startswith(("하지만 ", "그리고 ")) and len(text) > 45:
        return True
    return False


def infer_topic(text: str) -> str:
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return topic
    return "daily"


def infer_category(text: str) -> str:
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    if "?" in text:
        return "followup"
    return "reaction"


def score_candidate(text: str, topic: str, category: str) -> int:
    score = 0
    if 8 <= len(text) <= 48:
        score += 2
    if topic != "daily":
        score += 2
    if category in {"comfort", "decision", "encourage", "thanks"}:
        score += 2
    if "?" in text:
        score += 1
    if re.search(r"(좋아|괜찮|멋있|재밌|해봐|하자|그랬)", text):
        score += 1
    if text.startswith(("오 ", "아 ", "응", "좋아", "그렇", "괜찮")):
        score += 1
    if text.startswith(("나는", "나도", "내가")):
        score -= 3
    if topic == "daily" and category in {"reaction", "followup"}:
        score -= 1
    return score


def build_rows(candidates: list[SourceCandidate], *, max_per_alias: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    used_by_alias: dict[str, set[str]] = defaultdict(set)

    for candidate in candidates:
        for alias in route_aliases(candidate):
            if counts[alias] >= max_per_alias:
                continue
            if candidate.source_utterance in used_by_alias[alias]:
                continue
            style_alias = blended_style_alias(alias, candidate)
            airi_reply = minimal_polish(candidate.source_utterance, style_alias)
            if not airi_reply or reject_polished_reply(airi_reply):
                continue
            rows.append(
                {
                    "mbti_alias": alias,
                    "target_profile": ALIASES[alias],
                    "style_source_alias": style_alias,
                    "style_blend": "base_65" if style_alias == alias else "opposite_energy_35",
                    "profile_label": PROFILE_LABELS[alias],
                    "topic": candidate.topic,
                    "category": candidate.category,
                    "synthetic_user_message": synthesize_user_message(candidate, alias),
                    "source_utterance": candidate.source_utterance,
                    "airi_reply": airi_reply,
                    "source_score": str(candidate.score),
                    "source_split": candidate.source_split,
                    "source_id": candidate.source_id,
                    "source_index": str(candidate.source_index),
                    "keep_label": "",
                    "rewrite_reply": "",
                    "notes": "",
                }
            )
            counts[alias] += 1
            used_by_alias[alias].add(candidate.source_utterance)
        if all(counts[alias] >= max_per_alias for alias in ALIASES):
            break
    return rows


def route_aliases(candidate: SourceCandidate) -> tuple[str, ...]:
    text = candidate.source_utterance
    if candidate.category == "comfort":
        return ("i_f_n", "i_f_s", "e_f_s", "e_f_n")
    if candidate.category == "decision":
        return ("e_t_s", "i_t_s", "i_t_n", "e_t_n")
    if candidate.category == "thanks":
        return ("e_f_n", "e_f_s", "i_f_s", "i_f_n")
    if re.search(r"(해봐|하자|기준|먼저|일단)", text):
        return ("e_t_s", "i_t_s", "e_t_n", "i_t_n")
    if "?" in text:
        return ("e_f_n", "i_f_n", "e_t_n", "i_t_n")
    if candidate.topic in {"work", "game"}:
        return ("e_t_s", "i_t_s", "e_t_n", "i_t_n")
    if candidate.topic in {"movie", "music", "travel", "food", "sport"}:
        return ("e_f_n", "e_f_s", "i_f_n", "e_t_n")
    return ("e_f_n", "i_f_n", "i_f_s", "i_t_n")


def blended_style_alias(alias: str, candidate: SourceCandidate) -> str:
    seed = sum(ord(ch) for ch in candidate.source_utterance) + candidate.source_index
    if seed % 100 < 35:
        return OPPOSITE_ENERGY_ALIAS.get(alias, alias)
    return alias


def minimal_polish(text: str, style_alias: str) -> str:
    reply = text
    reply = re.sub(r"^(나는|나도|내가)\s+", "", reply)
    reply = reply.replace("하지 않아?", "하지?")
    reply = reply.replace("것 같아", "같아")
    reply = re.sub(r"\s+", " ", reply).strip()

    if style_alias in {"e_t_s", "i_t_s"}:
        reply = trim_to_sentences(reply, 1 if len(reply) > 34 else 2)
    elif style_alias in {"i_f_n", "i_f_s"}:
        reply = trim_to_sentences(reply, 2)
    else:
        reply = trim_to_sentences(reply, 2)

    return reply.strip()


def trim_to_sentences(text: str, max_sentences: int) -> str:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if not parts:
        return text
    return " ".join(parts[:max_sentences])


def reject_polished_reply(reply: str) -> bool:
    if len(reply) < 4 or len(reply) > 72:
        return True
    if re.search(r"\d+대\s*(남자|여자)", reply):
        return True
    if reply.startswith(("나는 ", "나도 ", "내가 ")):
        return True
    return False


def synthesize_user_message(candidate: SourceCandidate, alias: str) -> str:
    text = candidate.source_utterance
    topic = candidate.topic
    category = candidate.category

    if category == "comfort":
        if alias.startswith("i_f"):
            return "오늘 좀 마음이 무거워."
        return "오늘 진짜 기운 빠지는 일이 있었어."
    if category == "thanks":
        return "고마워. 방금 말 좋았어."
    if category == "decision":
        return "이거 어떻게 정리해서 보면 좋을까?"
    if re.search(r"(해봐|하자|먼저|일단)", text):
        return "뭘 먼저 해보면 좋을까?"
    if topic == "movie":
        return "영화 얘기 좀 해볼까?"
    if topic == "music":
        return "요즘 들을 음악 찾고 있어."
    if topic == "travel":
        return "요즘 어디론가 가보고 싶어."
    if topic == "food":
        return "오늘 뭐 먹을지 고민돼."
    if topic == "sport":
        return "운동을 시작해볼까 고민 중이야."
    if topic == "work":
        return "요즘 일이나 커리어 쪽이 좀 고민돼."
    if topic == "game":
        return "게임을 좀 더 잘하고 싶은데 감이 안 와."
    if "?" in text:
        return "나랑 이 얘기 조금 더 해볼래?"
    return "나랑 그냥 편하게 대화해줘."


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "mbti_alias",
        "target_profile",
        "style_source_alias",
        "style_blend",
        "profile_label",
        "topic",
        "category",
        "synthetic_user_message",
        "source_utterance",
        "airi_reply",
        "source_score",
        "source_split",
        "source_id",
        "source_index",
        "keep_label",
        "rewrite_reply",
        "notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
