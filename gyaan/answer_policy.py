from dataclasses import dataclass
import re


DETAIL_MARKERS = (
    "analyze",
    "comprehensive",
    "deep dive",
    "detail",
    "detailed",
    "explain fully",
    "in depth",
    "step by step",
    "thorough",
)
BRIEF_MARKERS = (
    "brief",
    "in one line",
    "one line",
    "quick answer",
    "short answer",
    "summarize",
)


@dataclass(frozen=True)
class AnswerPolicy:
    depth: str
    target_words: int
    reason: str


def choose_answer_policy(question: str, *, deep_research: bool = False) -> AnswerPolicy:
    lowered = question.lower()
    if deep_research or any(marker in lowered for marker in DETAIL_MARKERS):
        return AnswerPolicy(
            depth="detailed",
            target_words=900,
            reason="The user requested detailed analysis.",
        )
    if any(marker in lowered for marker in BRIEF_MARKERS):
        return AnswerPolicy(
            depth="brief",
            target_words=90,
            reason="The user explicitly requested a brief answer.",
        )

    words = re.findall(r"\b[\w'-]+\b", question)
    if len(words) <= 12 or lowered.startswith(("who ", "what ", "when ", "where ")):
        return AnswerPolicy(
            depth="brief",
            target_words=120,
            reason="This is a direct factual question.",
        )
    return AnswerPolicy(
        depth="standard",
        target_words=320,
        reason="The question needs explanation but not a full report.",
    )
