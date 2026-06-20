from dataclasses import dataclass


FRESHNESS_WORDS = {
    "today",
    "latest",
    "current",
    "recent",
    "news",
    "price",
    "score",
    "weather",
    "2025",
    "2026",
    "chief minister",
    "cm of",
    "current ceo",
    "current president",
    "current prime minister",
    "governor",
    "mayor",
    "minister",
    "president of",
    "prime minister",
    "who is",
}


@dataclass(frozen=True)
class RouteDecision:
    needs_web: bool
    reason: str
    model_roles: tuple[str, ...]
    research_mode: str = "quick"


def route_question(question: str, *, deep_research: bool = False) -> RouteDecision:
    """Choose whether GYAAAN should search the web and which model roles to run."""
    lowered = question.lower()
    needs_web = deep_research or any(word in lowered for word in FRESHNESS_WORDS)

    roles = ["reasoner", "summarizer"]
    if needs_web:
        roles.append("source_checker")
    if deep_research:
        roles.extend(("researcher", "critic"))
    if any(word in lowered for word in ("code", "python", "bug", "api", "error")):
        roles.append("coder")

    if deep_research:
        reason = (
            "Deep research was requested, so multiple searches and evidence checks "
            "are enabled."
        )
    elif needs_web:
        reason = "Question may depend on fresh information, so web search is enabled."
    else:
        reason = "Question looks answerable from model knowledge and reasoning."

    return RouteDecision(
        needs_web=needs_web,
        reason=reason,
        model_roles=tuple(dict.fromkeys(roles)),
        research_mode="deep" if deep_research else "quick",
    )
