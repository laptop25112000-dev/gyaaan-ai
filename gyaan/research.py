from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchPlan:
    queries: tuple[str, ...]
    evaluation_criteria: tuple[str, ...]


def build_research_plan(question: str) -> ResearchPlan:
    """Create complementary searches instead of repeating one broad query."""
    subject = question.strip().rstrip("?.") or "the topic"
    lowered = subject.lower()

    if any(word in lowered for word in ("restaurant", "restaurants", "food", "cafe")):
        queries = (
            subject,
            f"{subject} reviews ratings",
            f"{subject} menu prices cuisine",
            f"{subject} local recommendations",
            f"{subject} recent openings closures",
        )
        criteria = (
            "review consensus",
            "food quality",
            "price and value",
            "location and ambience",
            "freshness of information",
        )
    else:
        queries = (
            subject,
            f"{subject} authoritative sources",
            f"{subject} evidence and data",
            f"{subject} criticism conflicting views",
            f"{subject} latest developments",
        )
        criteria = (
            "source authority",
            "supporting evidence",
            "conflicting claims",
            "freshness",
        )

    return ResearchPlan(
        queries=tuple(dict.fromkeys(queries)),
        evaluation_criteria=criteria,
    )
