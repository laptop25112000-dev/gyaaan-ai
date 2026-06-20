import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .web_search import SearchResult


class LiveResearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class Citation:
    start_index: int
    end_index: int
    title: str
    url: str


@dataclass(frozen=True)
class LiveResearchResult:
    answer: str
    sources: list[SearchResult]
    citations: list[Citation]
    actions: list[str]


class OpenAIResearchClient:
    """Run agentic web research through the OpenAI Responses API."""

    endpoint = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gpt-5.5",
        timeout_seconds: int = 600,
        max_tool_calls: int = 20,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_tool_calls = max_tool_calls

    def research(self, question: str) -> LiveResearchResult:
        payload = {
            "model": self.model,
            "input": self._research_prompt(question),
            "tools": [{"type": "web_search"}],
            "tool_choice": "auto",
            "reasoning": {"effort": "high"},
            "text": {"verbosity": "high"},
            "max_tool_calls": self.max_tool_calls,
            "include": ["web_search_call.action.sources"],
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                data = json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            try:
                message = json.loads(detail)["error"]["message"]
            except (json.JSONDecodeError, KeyError, TypeError):
                message = detail or str(error)
            raise LiveResearchError(f"OpenAI research request failed: {message}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise LiveResearchError(
                f"Could not reach the OpenAI research service: {error}"
            ) from error

        if data.get("status") != "completed":
            error = data.get("error") or data.get("incomplete_details") or data["status"]
            raise LiveResearchError(f"Research did not complete: {error}")

        return self._parse_response(data)

    def _parse_response(self, data: dict) -> LiveResearchResult:
        answer_parts: list[str] = []
        citations: list[Citation] = []
        actions: list[str] = []
        source_by_url: dict[str, SearchResult] = {}
        answer_offset = 0

        for item in data.get("output", []):
            if item.get("type") == "web_search_call":
                action = item.get("action") or {}
                action_type = action.get("type", "search")
                detail = (
                    action.get("query")
                    or action.get("url")
                    or ", ".join(action.get("queries", []))
                    or "web"
                )
                actions.append(f"{action_type}: {detail}")
                for source in action.get("sources") or []:
                    self._add_source(source_by_url, source)
                continue

            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") != "output_text":
                    continue
                text = content.get("text", "")
                answer_parts.append(text)
                for annotation in content.get("annotations", []):
                    if annotation.get("type") != "url_citation":
                        continue
                    url = annotation.get("url", "")
                    title = annotation.get("title") or url
                    if not url:
                        continue
                    citations.append(
                        Citation(
                            start_index=answer_offset
                            + int(annotation.get("start_index", 0)),
                            end_index=answer_offset + int(annotation.get("end_index", 0)),
                            title=title,
                            url=url,
                        )
                    )
                    self._add_source(
                        source_by_url,
                        {"url": url, "title": title, "snippet": ""},
                    )
                answer_offset += len(text) + 2

        answer = "\n\n".join(part for part in answer_parts if part).strip()
        if not answer:
            raise LiveResearchError("The research service returned no report.")

        return LiveResearchResult(
            answer=answer,
            sources=list(source_by_url.values()),
            citations=citations,
            actions=actions,
        )

    @staticmethod
    def _add_source(
        source_by_url: dict[str, SearchResult], source: dict
    ) -> None:
        url = source.get("url", "")
        if not url or url in source_by_url:
            return
        source_by_url[url] = SearchResult(
            title=source.get("title") or url,
            url=url,
            snippet=source.get("snippet") or "",
        )

    @staticmethod
    def _research_prompt(question: str) -> str:
        return f"""Conduct rigorous web research for the user's question.

User question:
{question}

Search broadly from multiple angles. Open and inspect relevant pages instead of
relying only on search snippets. Prefer primary, authoritative, and recent
sources. Cross-check important claims, identify disagreements or uncertainty,
and do not invent facts.

Write a self-contained research report with:
- a concise executive summary;
- key findings organized under useful headings;
- comparison tables when they improve clarity;
- important caveats, conflicting evidence, and freshness limitations;
- a practical conclusion that directly answers the question.

Use inline citations for factual claims. Cite the strongest source near each
claim and include dates when freshness matters."""
