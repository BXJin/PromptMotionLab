from __future__ import annotations

import argparse
import ast
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


ORIGINAL_DIR = Path("Docs") / "Plan" / "10-RuntimeCharacter" / "data" / "original"
DEFAULT_OUT_DIR = Path("Build") / "reports" / "airi_style_candidates"
DOCS_CSV = Path("Docs") / "Plan" / "10-RuntimeCharacter" / "airi_source_utterance_candidates_v2.csv"

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

ALIAS_LABELS = {
    "e_f_n": "bright warm possibility",
    "e_f_s": "bright caring concrete",
    "e_t_n": "energetic analytical possibility",
    "e_t_s": "direct practical action",
    "i_f_n": "quiet warm reflective",
    "i_f_s": "quiet caring realistic",
    "i_t_n": "quiet structural reflective",
    "i_t_s": "quiet concise practical",
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

TOPIC_KEYWORDS = {
    "food": ("먹", "맛있", "음식", "카페", "커피", "과일", "복숭아", "저녁", "점심"),
    "movie": ("영화", "드라마", "멜로", "넷플", "장면"),
    "music": ("음악", "노래", "힙합", "가수", "듣"),
    "travel": ("여행", "바다", "산", "떠나", "가보고", "놀러"),
    "sport": ("운동", "농구", "수영", "스쿼시", "테니스", "헬스"),
    "work": ("회사", "이직", "직업", "준비", "면접", "커리어", "프로젝트", "일정", "작업"),
    "game": ("게임", "롤", "챔피언", "플레이"),
}

CATEGORY_KEYWORDS = {
    "comfort": ("힘들", "슬프", "외로", "우울", "걱정", "불안", "지쳐", "피곤", "속상", "괜찮"),
    "thanks": ("고마", "감사"),
    "decision": ("해야", "고민", "어떡", "어떻게", "결정", "선택", "기준"),
    "encourage": ("해봐", "하자", "좋아", "괜찮", "멋있", "재밌", "가능"),
    "analysis": ("이유", "원인", "구조", "중요", "먼저", "기준", "확인"),
}

REJECT_SUBSTRINGS = (
    "30대",
    "20대",
    "남자",
    "여자",
    "고양",
    "무역학과",
    "서기관",
    "부모님",
    "남편",
    "아내",
    "아들",
    "딸",
    "선생님",
    "학생",
    "반려자",
    "스위스",
    "출산",
    "딩크",
    "약을",
    "약 ",
    "알바",
    "진상",
    "직업이 뭐야",
    "점심시간",
    "식사는 했어",
    "잘 모르겠",
    "난 운동",
    "먹",
    "카페",
    "복숭아",
    "육회",
    "조개",
    "간장게장",
    "영화보고",
    "모바일 게임",
    "크아",
    "좋아하시나",
    "좋아하는",
    "좋아해",
    "없어?",
    "어때?",
    "있어?",
    "다녀?",
    "무슨 회사",
    "몇시까지",
)

GENERIC_BAD_PHRASES = (
    "도움이 필요하면",
    "언제든",
    "말씀해 주세요",
    "무엇을 도와",
    "제가 도와드릴",
)


@dataclass(frozen=True)
class Candidate:
    split: str
    source_id: str
    index: int
    utterance: str
    topic: str
    category: str
    score: int


def main() -> int:
    parser = argparse.ArgumentParser(description="Mine Airi source_utterance-first style candidates.")
    parser.add_argument("--max-per-alias", type=int, default=20)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--write-docs-copy", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    candidates = sorted(iter_candidates(), key=lambda item: item.score, reverse=True)
    rows = build_rows(candidates, max_per_alias=args.max_per_alias)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = args.out_dir / f"airi_source_utterance_candidates_v2_{timestamp}.csv"
    summary_path = args.out_dir / f"airi_source_utterance_candidates_v2_{timestamp}_summary.json"
    write_csv(csv_path, rows)
    if args.write_docs_copy:
        write_csv(DOCS_CSV, rows)

    summary = {
        "rows": len(rows),
        "maxPerAlias": args.max_per_alias,
        "counts": dict(sorted(Counter(row["mbti_alias"] for row in rows).items())),
        "uniqueSourceUtterances": len({row["source_utterance"] for row in rows}),
        "outputCsv": str(csv_path),
        "docsCopy": str(DOCS_CSV) if args.write_docs_copy else "",
        "method": "source_utterance_first_v2",
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def iter_candidates() -> Iterable[Candidate]:
    seen: set[str] = set()
    for split, path in source_files():
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                source_id = row.get("id", "")
                for index, utterance in enumerate(parse_dialog(row.get("session_dialog", ""))):
                    text = clean_text(utterance)
                    if text in seen or reject_utterance(text):
                        continue
                    topic = infer_topic(text)
                    category = infer_category(text)
                    score = score_candidate(text, topic, category)
                    if score < 5:
                        continue
                    seen.add(text)
                    yield Candidate(split, source_id, index, text, topic, category, score)


def source_files() -> Iterable[tuple[str, Path]]:
    yield "train", ORIGINAL_DIR / "banmal_train_8263.csv"
    yield "validation", ORIGINAL_DIR / "banmal_val_2066.csv"


def parse_dialog(value: str) -> list[str]:
    parsed = ast.literal_eval(value)
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().strip("\"' ")


def reject_utterance(text: str) -> bool:
    if len(text) < 7 or len(text) > 72:
        return True
    if not re.search(r"[가-힣]", text):
        return True
    if text.startswith(("안녕", "나는 ", "나도 ", "내가 ", "저는 ", "제가 ", "난 ")):
        return True
    if re.search(r"(^|[ ,.?!])나(는|도|랑|의|한테|에게)\b", text):
        return True
    if re.search(r"(^|[ ,.?!])내(가|게|겐|는|일|쪽)\b", text):
        return True
    if any(part in text for part in REJECT_SUBSTRINGS):
        return True
    if re.search(r"(뭐야\?|누구랑|어디야|얼마나|몇\s?시)", text):
        return True
    if any(part in text for part in GENERIC_BAD_PHRASES):
        return True
    if text.count("?") > 1:
        return True
    if re.search(r"(입니다|습니다|해주세요|하세요|드릴게요)", text):
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
    if 9 <= len(text) <= 46:
        score += 2
    if topic != "daily":
        score += 2
    if category in {"comfort", "decision", "analysis", "thanks"}:
        score += 2
    if category == "encourage" and not re.search(r"(먼저|일단|해보자|시작|정리|확인)", text):
        score -= 3
    if text.startswith(("아", "오", "응", "좋아", "그렇", "괜찮", "맞아", "음")):
        score += 1
    if "?" in text:
        score += 1
    if re.search(r"(먼저|일단|같이|천천히|해보자|좋겠|괜찮)", text):
        score += 1
    if re.search(r"(있어\?|좋아해\?|뭐야\?|누구랑|어디야)", text):
        score -= 2
    if topic == "daily" and category in {"reaction", "followup"}:
        score -= 1
    return score


def build_rows(candidates: list[Candidate], *, max_per_alias: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    used_by_alias: dict[str, set[str]] = {alias: set() for alias in ALIASES}
    for candidate in candidates:
        for alias in ranked_aliases(candidate):
            if counts[alias] >= max_per_alias or candidate.utterance in used_by_alias[alias]:
                continue
            style_alias = blended_alias(alias, candidate)
            airi_reply = polish_for_alias(candidate.utterance, style_alias)
            if reject_utterance(airi_reply):
                continue
            rows.append(
                {
                    "mbti_alias": alias,
                    "target_profile": ALIASES[alias],
                    "style_source_alias": style_alias,
                    "style_blend": "base_65" if style_alias == alias else "opposite_energy_35",
                    "alias_label": ALIAS_LABELS[alias],
                    "topic": candidate.topic,
                    "category": candidate.category,
                    "synthetic_user_message": synthesize_user_message(candidate, alias),
                    "source_utterance": candidate.utterance,
                    "airi_reply": airi_reply,
                    "source_score": str(candidate.score),
                    "source_split": candidate.split,
                    "source_id": candidate.source_id,
                    "source_index": str(candidate.index),
                    "keep_label": "",
                    "rewrite_reply": "",
                    "notes": "",
                }
            )
            counts[alias] += 1
            used_by_alias[alias].add(candidate.utterance)
        if all(counts[alias] >= max_per_alias for alias in ALIASES):
            break
    return rows


def ranked_aliases(candidate: Candidate) -> tuple[str, ...]:
    text = candidate.utterance
    if candidate.category == "comfort":
        return ("i_f_n", "i_f_s", "e_f_s", "e_f_n")
    if candidate.category in {"decision", "analysis"}:
        return ("e_t_s", "i_t_s", "i_t_n", "e_t_n")
    if candidate.category == "thanks":
        return ("e_f_n", "e_f_s", "i_f_s", "i_f_n")
    if re.search(r"(먼저|일단|해보자|확인|기준|정리)", text):
        return ("e_t_s", "i_t_s", "e_t_n", "i_t_n")
    if candidate.topic in {"work", "game"}:
        return ("e_t_s", "i_t_s", "e_t_n", "i_t_n")
    if candidate.topic in {"movie", "music", "travel", "food", "sport"}:
        return ("e_f_n", "e_f_s", "i_f_n", "e_t_n")
    if "?" in text:
        return ("e_f_n", "i_f_n", "e_t_n", "i_t_n")
    return ("i_f_s", "i_f_n", "e_f_s", "i_t_n")


def blended_alias(alias: str, candidate: Candidate) -> str:
    seed = sum(ord(ch) for ch in candidate.utterance) + candidate.index
    if seed % 100 < 35:
        return OPPOSITE_ENERGY_ALIAS[alias]
    return alias


def polish_for_alias(text: str, alias: str) -> str:
    reply = re.sub(r"\s+", " ", text).strip()
    reply = reply.replace("하지 않아?", "하지?")
    if alias in {"e_t_s", "i_t_s"} and len(reply) > 42:
        reply = first_sentence(reply)
    if alias.startswith("i_") and reply.startswith("응, "):
        reply = reply[3:]
    return reply


def first_sentence(text: str) -> str:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return parts[0] if parts else text


def synthesize_user_message(candidate: Candidate, alias: str) -> str:
    text = candidate.utterance
    if candidate.category == "comfort":
        return "오늘 좀 마음이 무거워."
    if candidate.category == "thanks":
        return "고마워. 방금 말 좋았어."
    if candidate.category in {"decision", "analysis"}:
        return "이거 어떻게 정리해서 보면 좋을까?"
    if re.search(r"(먼저|일단|해보자|확인|기준)", text):
        return "뭘 먼저 해보면 좋을까?"
    topic_prompts = {
        "food": "오늘 뭐 먹을지 고민돼.",
        "movie": "영화 얘기 좀 해볼까?",
        "music": "요즘 들을 음악 찾고 있어.",
        "travel": "요즘 어디론가 가보고 싶어.",
        "sport": "운동을 시작해볼까 고민 중이야.",
        "work": "요즘 일이나 커리어 쪽이 좀 고민돼.",
        "game": "게임을 좀 더 잘하고 싶은데 감이 안 와.",
    }
    if candidate.topic in topic_prompts:
        return topic_prompts[candidate.topic]
    if alias.startswith("i_"):
        return "나랑 조용히 얘기 좀 해줘."
    return "나랑 편하게 대화해줘."


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "mbti_alias",
        "target_profile",
        "style_source_alias",
        "style_blend",
        "alias_label",
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
