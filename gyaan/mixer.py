from dataclasses import dataclass

from .models import ModelResponse
from .prompts import MIXER_PROMPT
from .research import ResearchPlan
from .router import RouteDecision
from .web_search import SearchResult


@dataclass(frozen=True)
class MixedAnswer:
    mixer_model: str
    answer: str
    trace: str


class VivekMixer:
    """The final model-mixing layer. Public demo name: vivek3.0."""

    model_name = "vivek3.0"

    def mix(
        self,
        *,
        question: str,
        route: RouteDecision,
        search_results: list[SearchResult],
        model_responses: list[ModelResponse],
        research_plan: ResearchPlan | None = None,
    ) -> MixedAnswer:
        source_lines = [
            f"- {result.title}: {result.url}" for result in search_results
        ]
        response_lines = [
            f"- {response.role} via {response.model_name}: {response.content}"
            for response in model_responses
        ]

        if research_plan:
            answer_parts = self._deep_research_report(
                question, research_plan, search_results
            )
        else:
            answer_parts = [
                self._final_text(question, route, search_results),
            ]

        if search_results:
            answer_parts.extend(["", "Sources:", *source_lines])

        trace = "\n".join(
            [
                f"Mixer prompt: {MIXER_PROMPT.splitlines()[0]}",
                f"Router: {route.reason}",
                f"Research mode: {route.research_mode}",
                (
                    "Search queries: " + " | ".join(research_plan.queries)
                    if research_plan
                    else "Search queries: none"
                ),
                f"Roles: {', '.join(route.model_roles)}",
                "Model outputs:",
                *response_lines,
            ]
        )

        return MixedAnswer(
            mixer_model=self.model_name,
            answer="\n".join(answer_parts),
            trace=trace,
        )

    def _deep_research_report(
        self,
        question: str,
        plan: ResearchPlan,
        search_results: list[SearchResult],
    ) -> list[str]:
        evidence = [
            f"{index}. {result.title}: {result.snippet}"
            for index, result in enumerate(search_results, start=1)
        ]
        if not evidence:
            evidence = [
                "No evidence was returned. Configure a live search provider before "
                "using this report for a decision."
            ]

        return [
            f"GYAAAN deep research report mixed by {self.model_name}",
            "",
            f"Question: {question}",
            "",
            "Evaluation criteria:",
            *[f"- {criterion}" for criterion in plan.evaluation_criteria],
            "",
            "Evidence summary:",
            *evidence,
            "",
            "Research assessment:",
            (
                f"GYAAAN compared {len(search_results)} unique sources across "
                f"{len(plan.queries)} search angles. A live model provider should rank "
                "the candidates, reconcile conflicting reviews, and attach each "
                "recommendation to supporting evidence."
            ),
            "",
            "Limitations:",
            (
                "This installation is using its configured search/model providers. "
                "Verify availability, prices, ratings, and opening hours before acting."
            ),
        ]

    def _final_text(
        self,
        question: str,
        route: RouteDecision,
        search_results: list[SearchResult],
    ) -> str:
        if route.needs_web:
            return (
                "This question was routed through web search first, then checked by "
                "specialist model roles before being combined. Replace the demo search "
                "client with a real search API to make the citations live."
            )

        if "code" in question.lower() or "python" in question.lower():
            return (
                "This question needs a coding-capable model or live provider to produce "
                "a reliable implementation. GYAAAN identified it as a coding request."
            )

        return (
            "GYAAAN understood the question, but this offline demo provider does not "
            "contain a general knowledge model. Use the browser assistant for a "
            "source-backed answer."
        )
