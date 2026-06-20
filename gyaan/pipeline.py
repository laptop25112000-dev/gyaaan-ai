from dataclasses import dataclass

from .answer_policy import AnswerPolicy, choose_answer_policy
from .config import Settings, load_settings
from .live_research import Citation, OpenAIResearchClient
from .mixer import MixedAnswer, VivekMixer
from .models import DemoModelClient, ModelClient, model_name_for_role
from .public_research import PublicWebResearchClient
from .research import ResearchPlan, build_research_plan
from .router import RouteDecision, route_question
from .web_search import DemoWebSearchClient, SearchResult, WebSearchClient


@dataclass(frozen=True)
class GyaanRun:
    question: str
    route: RouteDecision
    search_results: list[SearchResult]
    final: MixedAnswer
    research_plan: ResearchPlan | None = None
    citations: tuple[Citation, ...] = ()
    research_actions: tuple[str, ...] = ()
    provider: str = "demo"
    answer_policy: AnswerPolicy | None = None


class GyaanPipeline:
    def __init__(
        self,
        *,
        search_client: WebSearchClient | None = None,
        model_client: ModelClient | None = None,
        mixer: VivekMixer | None = None,
        settings: Settings | None = None,
        research_client: object | None = None,
        use_live_answers: bool = False,
    ) -> None:
        self.settings = settings or load_settings()
        self.search_client = search_client or DemoWebSearchClient()
        self.model_client = model_client or DemoModelClient()
        self.mixer = mixer or VivekMixer()
        self.use_live_answers = use_live_answers
        self.research_client = research_client
        if (
            self.research_client is None
            and self.settings.research_provider == "openai"
            and self.settings.openai_api_key
        ):
            self.research_client = OpenAIResearchClient(
                self.settings.openai_api_key,
                model=self.settings.research_model,
                max_tool_calls=self.settings.research_max_tool_calls,
            )
        if self.research_client is None and search_client is None:
            self.research_client = PublicWebResearchClient()

    @property
    def live_research_available(self) -> bool:
        return self.research_client is not None

    def ask(self, question: str, *, deep_research: bool = False) -> GyaanRun:
        route = route_question(question, deep_research=deep_research)
        answer_policy = choose_answer_policy(
            question, deep_research=deep_research
        )
        research_plan = build_research_plan(question) if deep_research else None

        if (
            deep_research or route.needs_web or self.use_live_answers
        ) and self.research_client:
            if deep_research:
                result = self.research_client.research(question)
            else:
                quick_research = getattr(self.research_client, "answer", None)
                result = (
                    quick_research(question, depth=answer_policy.depth)
                    if quick_research
                    else self.research_client.research(question)
                )
            action_lines = "\n".join(f"- {action}" for action in result.actions)
            trace = "\n".join(
                [
                    f"Provider: {type(self.research_client).__name__}",
                    f"Research mode: {route.research_mode}",
                    f"Answer depth: {answer_policy.depth}",
                    f"Web actions: {len(result.actions)}",
                    action_lines or "- Search actions were not returned by the API.",
                    f"Cited sources: {len(result.sources)}",
                ]
            )
            return GyaanRun(
                question=question,
                route=route,
                search_results=result.sources,
                final=MixedAnswer(
                    mixer_model=self.settings.research_model,
                    answer=result.answer,
                    trace=trace,
                ),
                research_plan=research_plan,
                citations=tuple(result.citations),
                research_actions=tuple(result.actions),
                provider=(
                    "openai"
                    if isinstance(self.research_client, OpenAIResearchClient)
                    else "public-web"
                ),
                answer_policy=answer_policy,
            )

        if research_plan:
            search_results = self._run_deep_search(research_plan)
        elif route.needs_web:
            search_results = self.search_client.search(
                question, limit=self.settings.max_sources
            )
        else:
            search_results = []

        model_responses = [
            self.model_client.complete(
                model_name=model_name_for_role(role),
                role=role,
                question=question,
                search_results=search_results,
            )
            for role in route.model_roles
        ]

        final = self.mixer.mix(
            question=question,
            route=route,
            search_results=search_results,
            model_responses=model_responses,
            research_plan=research_plan,
        )
        return GyaanRun(
            question=question,
            route=route,
            search_results=search_results,
            final=final,
            research_plan=research_plan,
            provider="demo",
            answer_policy=answer_policy,
        )

    def _run_deep_search(self, plan: ResearchPlan) -> list[SearchResult]:
        results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for query in plan.queries:
            query_results = self.search_client.search(
                query,
                limit=self.settings.sources_per_research_query,
            )
            for result in query_results:
                if result.url in seen_urls:
                    continue
                seen_urls.add(result.url)
                results.append(result)
                if len(results) >= self.settings.deep_research_sources:
                    return results

        return results
