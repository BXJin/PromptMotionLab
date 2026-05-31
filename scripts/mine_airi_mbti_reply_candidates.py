from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
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

PROFILE_META = {
    "e_f_n": ("bright", "outgoing, feeling, intuitive"),
    "e_f_s": ("cheerful", "outgoing, feeling, sensing"),
    "e_t_n": ("idea", "outgoing, thinking, intuitive"),
    "e_t_s": ("direct", "outgoing, thinking, sensing"),
    "i_f_n": ("soft", "introverted, feeling, intuitive"),
    "i_f_s": ("calm", "introverted, feeling, sensing"),
    "i_t_n": ("reflective", "introverted, thinking, intuitive"),
    "i_t_s": ("practical", "introverted, thinking, sensing"),
}

PROFILE_LIMITS = {
    "e_f_n": 45,
    "e_f_s": 45,
    "e_t_n": 45,
    "e_t_s": 45,
    "i_f_n": 45,
    "i_f_s": 45,
    "i_t_n": 45,
    "i_t_s": 45,
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

REJECT_PATTERNS = (
    r"^안녕,?\s*나는",
    r"나는\s+\d+대",
    r"\d+대\s*(남자|여자)",
    r"나는\s+.*(살아|산다|전공|직업|남자|여자)",
    r"(우리\s+)?부모님",
    r"남편|아내|아들|딸",
    r"초등학교|중학교|고등학교|대학교",
)

GENERIC_BAD_PHRASES = (
    "도움이 필요하면",
    "언제든",
    "무엇을 도와",
    "말씀해 주세요",
)

CATEGORY_KEYWORDS = {
    "comfort": ("힘들", "슬프", "외로", "우울", "걱정", "불안", "지쳤", "피곤", "속상"),
    "thanks": ("고마", "감사"),
    "decision": ("해야", "고민", "어떡", "어떻게", "결정", "선택"),
    "interest": ("좋아", "재밌", "멋있", "신나", "보고 싶", "해보고"),
    "work": ("회사", "이직", "일", "준비", "면접", "포트폴리오"),
    "game": ("게임", "롤", "챔피언", "플레이", "연습"),
}


@dataclass(frozen=True)
class Candidate:
    source_id: str
    source_split: str
    source_index: int
    source_utterance: str
    category: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mine Korean persona-chat utterances into Airi MBTI-style reply candidates."
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max-per-alias", type=int, default=45)
    parser.add_argument("--splits", nargs="*", default=["train", "validation"])
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    candidates = list(iter_candidates(args.splits))
    rows = build_rows(candidates, max_per_alias=args.max_per_alias)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = args.out_dir / f"airi_mbti_reply_mining_candidates_{timestamp}.csv"
    summary_path = args.out_dir / f"airi_mbti_reply_mining_candidates_{timestamp}_summary.json"

    write_csv(csv_path, rows)
    counts = defaultdict(int)
    for row in rows:
        counts[row["mbti_alias"]] += 1
    summary = {
        "rows": len(rows),
        "counts": dict(sorted(counts.items())),
        "source": "Docs/Plan/10-RuntimeCharacter/data/jsonl",
        "note": "Synthetic user messages were generated from mined reply-like utterances; human labeling is required.",
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"CSV={csv_path}")
    print(f"SUMMARY={summary_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def iter_candidates(splits: Iterable[str]) -> Iterable[Candidate]:
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
                    if text in seen or reject_utterance(text):
                        continue
                    category = classify(text)
                    if category == "other":
                        continue
                    seen.add(text)
                    yield Candidate(
                        source_id=source_id,
                        source_split=split,
                        source_index=index,
                        source_utterance=text,
                        category=category,
                    )


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip("\"' ")


def reject_utterance(text: str) -> bool:
    if len(text) < 5 or len(text) > 62:
        return True
    if not re.search(r"[가-힣]", text):
        return True
    if text.count("?") > 2:
        return True
    if any(phrase in text for phrase in GENERIC_BAD_PHRASES):
        return True
    if any(re.search(pattern, text) for pattern in REJECT_PATTERNS):
        return True
    if text.startswith(("나는 ", "나도 ", "내가 ")):
        return True
    if text.startswith(("그리고 ", "하지만 ", "근데 ")) and len(text) > 45:
        return True
    return False


def classify(text: str) -> str:
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    if "?" in text:
        return "followup"
    return "casual"


def build_rows(candidates: list[Candidate], *, max_per_alias: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    counts: dict[str, int] = defaultdict(int)

    for candidate in candidates:
        for alias in route_aliases(candidate):
            limit = min(max_per_alias, PROFILE_LIMITS.get(alias, max_per_alias))
            if counts[alias] >= limit:
                continue
            user_message = synthesize_user_message(alias, candidate)
            style_alias = blended_style_alias(alias, candidate)

            rows.append(
                {
                    "mbti_alias": alias,
                    "target_profile": ALIASES[alias],
                    "style_source_alias": style_alias,
                    "style_blend": "base_65" if style_alias == alias else "opposite_energy_35",
                    "profile_label": PROFILE_META[alias][0],
                    "mbti_interpretation": PROFILE_META[alias][1],
                    "category": candidate.category,
                    "topic": infer_topic(candidate.source_utterance),
                    "synthetic_user_message": user_message,
                    "source_utterance": candidate.source_utterance,
                    "airi_reply": rewrite_for_alias(style_alias, candidate.source_utterance, candidate.category),
                    "source_split": candidate.source_split,
                    "source_id": candidate.source_id,
                    "source_index": str(candidate.source_index),
                    "keep_label": "",
                    "rewrite_reply": "",
                    "notes": "",
                }
            )
            counts[alias] += 1

        if all(counts[alias] >= max_per_alias for alias in ALIASES):
            break

    return rows


def blended_style_alias(alias: str, candidate: Candidate) -> str:
    """Keep the selected MBTI alias, but mix in the E/I opposite style about 35% of the time."""
    seed = sum(ord(ch) for ch in candidate.source_utterance) + candidate.source_index
    if seed % 100 < 35:
        return OPPOSITE_ENERGY_ALIAS.get(alias, alias)
    return alias


def route_aliases(candidate: Candidate) -> tuple[str, ...]:
    category = candidate.category
    if category == "comfort":
        return ("i_f_n", "i_f_s", "e_f_s")
    if category == "thanks":
        return ("e_f_n", "e_f_s", "i_f_s")
    if category == "decision":
        return ("e_t_s", "i_t_s", "i_t_n")
    if category == "interest":
        return ("e_f_n", "e_t_n", "i_f_n")
    if category in {"work", "game"}:
        return ("e_t_s", "i_t_s", "e_t_n")
    if category == "followup":
        return ("airi",) if False else ("e_f_n", "i_f_n", "i_t_n")
    if category == "casual":
        return tuple(ALIASES)
    return tuple(ALIASES)


def synthesize_user_message(alias: str, candidate: Candidate) -> str:
    category = candidate.category
    text = candidate.source_utterance
    topic = infer_topic(text)
    if category == "comfort":
        return pick_variant(
            candidate,
            [
                pick_by_alias(
                    alias,
                    {
                        "e_f": "오늘 진짜 기운 빠지는 일이 있었어.",
                        "i_f": "오늘 좀 마음이 무거워.",
                        "t": "오늘 컨디션이 별로라 집중이 안 돼.",
                    },
                ),
                "오늘 별일 아닌데도 좀 지쳐.",
                "괜찮은 척은 하는데 사실 좀 힘들어.",
                "오늘은 그냥 누가 내 편이면 좋겠어.",
            ],
        )
    if category == "thanks":
        return pick_variant(
            candidate,
            [
                pick_by_alias(
                    alias,
                    {
                        "e": "고마워, 방금 말 좀 좋았다.",
                        "i": "고마워. 조금 편해졌어.",
                        "t": "좋아, 그 방식 괜찮네. 고마워.",
                    },
                ),
                "고마워. 생각보다 도움이 됐어.",
                "방금 말은 좀 마음에 들었어.",
                "오케이, 그렇게 해볼게. 고마워.",
            ],
        )
    if category == "decision":
        if alias in {"e_t_s", "i_t_s"}:
            return pick_variant(
                candidate,
                [
                    "이거 어떻게 정리해서 진행하는 게 나을까?",
                    "지금 뭘 먼저 해야 할지 정리가 안 돼.",
                    "선택지가 많은데 기준을 못 잡겠어.",
                ],
            )
        return pick_variant(
            candidate,
            [
                "생각이 좀 꼬였어. 어디부터 봐야 할까?",
                "머릿속이 복잡해서 같이 정리해줬으면 해.",
                "결정은 해야 하는데 감이 안 와.",
            ],
        )
    if category == "interest":
        if topic == "movie":
            return pick_variant(candidate, ["오늘 영화 이야기 좀 하고 싶어.", "최근에 본 영화 얘기하고 싶어.", "영화 고르는 기준이 좀 궁금해."])
        if topic == "travel":
            return pick_variant(candidate, ["요즘 어디론가 가보고 싶어.", "여행 가고 싶은데 어디가 좋을까?", "잠깐 떠나고 싶은 기분이야."])
        if topic == "music":
            return pick_variant(candidate, ["요즘 들을 음악 찾고 있어.", "내 취향에 맞는 노래를 찾고 싶어.", "음악 얘기 좀 해볼까?"])
        if topic == "food":
            return pick_variant(candidate, ["요즘 맛있는 거 먹는 얘기 하고 싶어.", "오늘 뭐 먹으면 좋을까?", "맛있는 걸로 기분 전환하고 싶어."])
        if topic == "sport":
            return pick_variant(candidate, ["운동을 시작해볼까 고민 중이야.", "가볍게 할 운동 뭐가 좋을까?", "몸을 좀 움직여야 할 것 같아."])
        return pick_variant(candidate, ["나 요즘 재밌는 거 하나 찾고 싶어.", "새로운 취미 하나 있으면 좋겠어.", "요즘 뭔가 끌리는 게 별로 없어."])
    if category == "work":
        return pick_variant(candidate, ["요즘 일이나 커리어 쪽이 좀 고민돼.", "일 때문에 생각이 많아.", "커리어 방향을 다시 봐야 할 것 같아."])
    if category == "game":
        return pick_variant(candidate, ["게임을 좀 더 잘하고 싶은데 감이 안 와.", "롤을 잘하고 싶은데 어디부터 고쳐야 할까?", "게임 실력이 막힌 느낌이야."])
    if category == "followup":
        return pick_variant(
            candidate,
            [
                topic_user_message(topic),
                "그 얘기 조금 더 해볼까?",
                "그 주제로 편하게 얘기해줘.",
                "방금 얘기에서 이어서 말해줘.",
                "그런 상황이면 넌 뭐라고 할 것 같아?",
                "나한테 친구처럼 한마디 해줘.",
            ],
        )
    return pick_variant(candidate, daily_user_variants())


def rewrite_for_alias(alias: str, source: str, category: str) -> str:
    topic = infer_topic(source)
    base = strip_excess(strip_persona_claims(source))

    if alias == "e_t_s":
        return direct_reply(base, category, topic)
    if alias == "i_t_s":
        return practical_reply(base, category, topic)
    if alias == "i_t_n":
        return reflective_reply(base, category, topic)
    if alias == "i_f_n":
        return soft_reply(base, category, topic)
    if alias == "i_f_s":
        return calm_reply(base, category, topic)
    if alias == "e_f_n":
        return bright_reply(base, category, topic)
    if alias == "e_f_s":
        return cheerful_reply(base, category, topic)
    if alias == "e_t_n":
        return idea_reply(base, category, topic)
    return base


def strip_persona_claims(text: str) -> str:
    text = re.sub(r"^(나는|나도|내가)\s+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_excess(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text)
    if len(parts) > 2:
        return " ".join(parts[:2]).strip()
    return text


def direct_reply(base: str, category: str, topic: str) -> str:
    if category in {"decision", "work", "game"}:
        return "좋아. 일단 기준 하나만 잡고 바로 좁혀보자."
    if category == "comfort":
        return "그건 꽤 지칠 만해. 지금은 억지로 괜찮은 척 안 해도 돼."
    if category in {"interest", "followup", "casual"}:
        return direct_topic_reply(topic)
    return tighten(base)


def practical_reply(base: str, category: str, topic: str) -> str:
    if category in {"decision", "work", "game"}:
        return "먼저 목표, 제약, 다음 행동을 나눠보자. 거기서 답이 빨리 나와."
    if category == "comfort":
        return "오늘은 판단을 줄이고 쉬는 쪽이 낫겠다."
    if category in {"interest", "followup", "casual"}:
        return practical_topic_reply(topic)
    return tighten(base)


def reflective_reply(base: str, category: str, topic: str) -> str:
    if category in {"decision", "work"}:
        return "지금은 선택지가 많은 게 아니라 기준이 흐린 상태 같아."
    if category == "comfort":
        return "그 감정은 그냥 지나가는 게 아니라, 뭔가 쌓였다는 신호일 수 있어."
    if category in {"interest", "followup", "casual"}:
        return reflective_topic_reply(topic)
    return base


def soft_reply(base: str, category: str, topic: str) -> str:
    if category == "comfort":
        return "아... 그런 날 있지. 말하기 어려우면 천천히 말해도 돼."
    if category == "thanks":
        return "응, 그렇게 말해줘서 나도 좋아."
    if category in {"interest", "followup", "casual"}:
        return soft_topic_reply(topic)
    return soften(base)


def calm_reply(base: str, category: str, topic: str) -> str:
    if category == "comfort":
        return "그랬구나. 지금은 조금 내려놓고 숨부터 쉬어도 돼."
    if category in {"decision", "work"}:
        return "좋아. 급하게 결론 내기보다 하나씩 나눠보자."
    if category in {"interest", "followup", "casual"}:
        return calm_topic_reply(topic)
    return soften(base)


def bright_reply(base: str, category: str, topic: str) -> str:
    if category == "thanks":
        return "응, 당연하지. 그런 말 들으니까 나도 기분 좋다."
    if category == "interest":
        return bright_topic_reply(topic)
    if category in {"followup", "casual"}:
        return bright_topic_reply(topic)
    return base


def cheerful_reply(base: str, category: str, topic: str) -> str:
    if category == "comfort":
        return "아, 그랬구나. 오늘은 내가 네 편 들어줄게."
    if category == "thanks":
        return "응, 나한테도 그런 말 꽤 좋다."
    if category in {"interest", "followup", "casual"}:
        return cheerful_topic_reply(topic)
    return base


def idea_reply(base: str, category: str, topic: str) -> str:
    if category in {"decision", "work", "game"}:
        return "각도를 바꿔보자. 지금 필요한 건 큰 답보다 바로 해볼 작은 실험 같아."
    if category == "interest":
        return "그거에서 시작하면 좋겠다. 취향을 하나 잡고 비슷한 걸 넓혀보자."
    if category in {"followup", "casual"}:
        return idea_topic_reply(topic)
    return base


def infer_topic(text: str) -> str:
    if any(word in text for word in ("영화", "드라마", "넷플", "멜로")):
        return "movie"
    if any(word in text for word in ("음악", "힙합", "노래", "가수")):
        return "music"
    if any(word in text for word in ("여행", "바다", "산", "스위스", "제주")):
        return "travel"
    if any(word in text for word in ("음식", "먹", "맛있", "카페", "커피")):
        return "food"
    if any(word in text for word in ("운동", "농구", "수영", "테니스", "스쿼시")):
        return "sport"
    if any(word in text for word in ("회사", "이직", "면접", "일", "직업")):
        return "work"
    if any(word in text for word in ("게임", "롤", "챔피언")):
        return "game"
    return "daily"


def pick_by_alias(alias: str, options: dict[str, str]) -> str:
    if alias.startswith("e_f") and "e_f" in options:
        return options["e_f"]
    if alias.startswith("i_f") and "i_f" in options:
        return options["i_f"]
    if "_t_" in alias and "t" in options:
        return options["t"]
    if alias.startswith("e") and "e" in options:
        return options["e"]
    if alias.startswith("i") and "i" in options:
        return options["i"]
    return next(iter(options.values()))


def pick_variant(candidate: Candidate, options: list[str]) -> str:
    seed = sum(ord(ch) for ch in candidate.source_utterance) + candidate.source_index
    return options[seed % len(options)]


def topic_user_message(topic: str) -> str:
    return {
        "movie": "요즘 볼 만한 영화 이야기 해볼까?",
        "music": "요즘 음악 취향이 좀 바뀐 것 같아.",
        "travel": "여행 가고 싶은데 어디가 좋을지 모르겠어.",
        "food": "오늘 뭐 먹을지 고민돼.",
        "sport": "운동 얘기 좀 해보고 싶어.",
        "work": "일 쪽으로 생각이 좀 많아.",
        "game": "게임 얘기 좀 해보자.",
        "daily": "오늘 그냥 소소한 얘기 하고 싶어.",
    }[topic]


def daily_user_variants() -> list[str]:
    return [
        "나랑 그냥 편하게 대화해줘.",
        "오늘은 가볍게 수다 떨고 싶어.",
        "특별한 건 없고 그냥 얘기하고 싶어.",
        "친구처럼 짧게 받아줘.",
        "뭔가 대단한 답 말고 자연스럽게 말해줘.",
        "오늘 있었던 일에 그냥 반응해줘.",
        "딱딱한 말투 말고 편하게 얘기해줘.",
        "지금 그냥 누가 말 걸어주면 좋겠어.",
        "별 얘기 아닌데 같이 얘기해줘.",
        "너라면 이럴 때 뭐라고 해?",
        "나 지금 조금 심심해.",
        "그냥 자연스럽게 이어가줘.",
        "내 말에 너무 설명 말고 반응해줘.",
        "친한 친구처럼 답해줘.",
        "요즘 대화가 좀 필요해.",
        "별건 아닌데 얘기 좀 들어줘.",
        "오늘 기분이 애매해.",
        "가볍게 한마디 해줘.",
        "지금 분위기에 맞게 말해줘.",
        "나랑 조금 더 얘기하자.",
    ]


def bright_topic_reply(topic: str) -> str:
    return {
        "movie": "오, 영화 얘기 좋다. 오늘은 가볍게 빠져들 만한 걸로 골라보자.",
        "music": "좋지. 지금 기분에 맞는 노래 찾는 것도 꽤 재밌어.",
        "travel": "와, 여행 얘기는 벌써 기분 좋아진다. 어디 분위기가 끌려?",
        "food": "좋아. 오늘은 맛있는 걸로 기분 좀 올려야지.",
        "sport": "오, 운동 좋다. 처음엔 가볍게 움직이는 쪽이 덜 부담돼.",
        "work": "좋아, 일 얘기면 감정이랑 현실을 나눠서 보자.",
        "game": "좋아, 게임은 한 번에 다 잘하려고 하면 더 꼬여.",
        "daily": "좋아, 그런 얘기 은근 재밌어. 오늘 뭐가 제일 기억나?",
    }[topic]


def cheerful_topic_reply(topic: str) -> str:
    return {
        "movie": "영화 얘기 좋다. 보고 나서 남는 장면 하나 있으면 그게 진짜야.",
        "music": "음악은 기분 바꾸는 데 꽤 세지. 지금은 어떤 분위기가 좋아?",
        "travel": "어디론가 가고 싶은 마음이면 이미 반쯤 출발한 거지.",
        "food": "오늘은 맛있는 걸로 가자. 기분 전환엔 그게 제일 빠를 때도 있어.",
        "sport": "운동은 너무 거창하게 시작 안 해도 돼. 조금만 해도 티 나.",
        "work": "일 고민은 혼자 들고 있으면 더 커져. 하나씩 꺼내보자.",
        "game": "게임은 재밌게 해야 오래 가. 일단 한 가지만 잡자.",
        "daily": "응, 그런 소소한 얘기 좋아. 편하게 말해봐.",
    }[topic]


def soft_topic_reply(topic: str) -> str:
    return {
        "movie": "영화 얘기 좋다. 어떤 장면이 마음에 남았는지 궁금해.",
        "music": "그럴 때 음악 찾는 거 좋지. 지금 마음이랑 맞는 소리가 있을 거야.",
        "travel": "어딘가 가고 싶은 마음이 드는 날이 있지. 조금 멀어지고 싶은 걸지도 몰라.",
        "food": "그럴 땐 따뜻하고 익숙한 게 좋을 때도 있어.",
        "sport": "무리하지 말고 천천히 움직여도 괜찮아.",
        "work": "일 얘기는 마음도 같이 얽히니까, 천천히 풀어보자.",
        "game": "잘하고 싶은 마음이 있으면 이미 꽤 좋아하는 거네.",
        "daily": "응, 오늘은 그냥 편하게 얘기해도 돼.",
    }[topic]


def calm_topic_reply(topic: str) -> str:
    return {
        "movie": "좋아. 가볍게 하나 고르고, 보고 난 느낌부터 얘기하면 돼.",
        "music": "지금 기분에 맞는 걸로 고르면 돼. 너무 많이 찾을 필요는 없어.",
        "travel": "먼저 바다인지 도시인지부터 나눠보자.",
        "food": "간단하게 가자. 지금 먹고 싶은 맛부터 정하면 돼.",
        "sport": "처음엔 오래보다 꾸준한 쪽이 좋아.",
        "work": "일단 상황, 감정, 선택지를 따로 놓고 보자.",
        "game": "한 판마다 하나씩만 고치면 돼.",
        "daily": "응. 오늘 있었던 일부터 천천히 얘기해봐.",
    }[topic]


def direct_topic_reply(topic: str) -> str:
    return {
        "movie": "좋아. 장르부터 정하자. 그래야 고르기 쉬워.",
        "music": "먼저 분위기부터 잡자. 신나는 쪽인지 차분한 쪽인지.",
        "travel": "거리, 예산, 분위기. 이 세 개부터 정하면 돼.",
        "food": "지금은 메뉴보다 맛 방향부터 정해. 매운지 담백한지.",
        "sport": "처음엔 장비 적고 바로 할 수 있는 운동이 좋아.",
        "work": "좋아. 원인, 선택지, 다음 행동으로 쪼개자.",
        "game": "챔피언 하나만 고정해. 그게 제일 빨라.",
        "daily": "좋아. 핵심만 말해봐. 내가 같이 정리해볼게.",
    }[topic]


def practical_topic_reply(topic: str) -> str:
    return {
        "movie": "후보 세 개만 고르고 하나씩 지워보자.",
        "music": "플레이리스트 하나 만들고, 안 맞는 곡만 빼면 돼.",
        "travel": "먼저 당일치기인지 숙박인지 정하자.",
        "food": "배달, 외식, 집밥 중 하나부터 정하면 빨라.",
        "sport": "주 2회, 20분부터 시작하는 게 현실적이야.",
        "work": "지금 필요한 건 감정 정리보다 조건 정리야.",
        "game": "리플레이 하나 보고 죽은 이유만 적어봐.",
        "daily": "좋아. 복잡하게 말고 하나씩만 꺼내보자.",
    }[topic]


def reflective_topic_reply(topic: str) -> str:
    return {
        "movie": "끌리는 장르를 보면 지금 기분도 조금 보일 때가 있어.",
        "music": "듣고 싶은 음악은 가끔 지금 감정의 모양을 보여줘.",
        "travel": "어디를 가고 싶은지보다 왜 떠나고 싶은지가 더 중요할 수도 있어.",
        "food": "먹고 싶은 게 없다는 것도 컨디션 신호일 수 있어.",
        "sport": "운동은 몸을 움직이는 일이지만, 리듬을 다시 잡는 일이기도 해.",
        "work": "지금 고민은 일 자체보다 방향감 문제에 가까워 보여.",
        "game": "실력이 막힌 게 아니라 보는 기준이 아직 덜 잡힌 걸 수 있어.",
        "daily": "소소한 얘기에서 오히려 지금 상태가 잘 보일 때가 있어.",
    }[topic]


def idea_topic_reply(topic: str) -> str:
    return {
        "movie": "테마를 하나 잡아보자. 오늘은 반전, 위로, 액션 중 하나로.",
        "music": "기분 키워드 하나로 찾아보자. 밤, 산책, 집중 같은 식으로.",
        "travel": "목적지를 고르기 전에 컨셉을 잡자. 쉬기, 걷기, 사진.",
        "food": "오늘의 기준을 하나만 잡자. 든든함인지 새로움인지.",
        "sport": "게임처럼 해보자. 이번 주 목표는 출석 체크 정도로.",
        "work": "문제를 바로 풀지 말고, 먼저 이름을 붙여보자.",
        "game": "연습을 퀘스트처럼 쪼개면 덜 지루해져.",
        "daily": "좋아. 오늘 일을 하나의 장면처럼 보면 뭐가 남아?",
    }[topic]


def tighten(text: str) -> str:
    text = text.replace("것 같아", "같아")
    text = text.replace("하지 않아?", "하지?")
    return text


def soften(text: str) -> str:
    if text.endswith("?"):
        return text
    if len(text) < 32:
        return f"{text}."
    return text


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "mbti_alias",
        "target_profile",
        "style_source_alias",
        "style_blend",
        "profile_label",
        "mbti_interpretation",
        "category",
        "topic",
        "synthetic_user_message",
        "source_utterance",
        "airi_reply",
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
