import html
import re
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from html.parser import HTMLParser

from .live_research import Citation, LiveResearchError, LiveResearchResult
from .research import build_research_plan
from .web_search import SearchResult


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
STOP_WORDS = {
    "about",
    "after",
    "also",
    "and",
    "are",
    "best",
    "can",
    "for",
    "from",
    "have",
    "how",
    "into",
    "latest",
    "more",
    "most",
    "not",
    "search",
    "that",
    "the",
    "their",
    "this",
    "what",
    "when",
    "where",
    "which",
    "with",
}


@dataclass(frozen=True)
class PageContent:
    title: str
    url: str
    text: str


class SearchResultsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[SearchResult] = []
        self._href = ""
        self._parts: list[str] = []
        self._capturing = False
        self._capturing_snippet = False
        self._snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "a" and "result__a" in classes:
            self._href = attributes.get("href") or ""
            self._parts = []
            self._capturing = True
        elif "result__snippet" in classes:
            self._snippet_parts = []
            self._capturing_snippet = True

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._parts.append(data)
        if self._capturing_snippet:
            self._snippet_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capturing:
            self._capturing = False
            url = unwrap_duckduckgo_url(self._href)
            title = clean_text(" ".join(self._parts))
            if url and title:
                self.results.append(SearchResult(title=title, url=url, snippet=""))
        if self._capturing_snippet and tag in {"a", "div", "span"}:
            self._capturing_snippet = False
            snippet = clean_text(" ".join(self._snippet_parts))
            if self.results and snippet:
                result = self.results[-1]
                self.results[-1] = SearchResult(
                    title=result.title,
                    url=result.url,
                    snippet=snippet,
                )


class BraveSearchParser(HTMLParser):
    BLOCKED_HOSTS = {
        "cdn.search.brave.com",
        "search.brave.com",
        "www.instagram.com",
        "www.youtube.com",
        "youtube.com",
    }

    def __init__(self) -> None:
        super().__init__()
        self.results: list[SearchResult] = []
        self._href = ""
        self._parts: list[str] = []
        self._capturing = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attributes = dict(attrs)
        href = html.unescape(attributes.get("href") or "")
        classes = (attributes.get("class") or "").split()
        parsed = urllib.parse.urlparse(href)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.netloc in self.BLOCKED_HOSTS
            or "thumbnail" in classes
        ):
            return
        self._href = href
        self._parts = []
        self._capturing = True

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._capturing:
            return
        self._capturing = False
        title = clean_text(" ".join(self._parts))
        if len(title) < 4:
            return
        self.results.append(
            SearchResult(title=title[:240], url=self._href, snippet="")
        )


class ArticleParser(HTMLParser):
    BLOCK_TAGS = {
        "article",
        "blockquote",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "li",
        "main",
        "p",
        "section",
        "td",
    }
    IGNORED_TAGS = {"aside", "footer", "form", "nav", "noscript", "script", "style", "svg"}

    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._title_parts: list[str] = []
        self._blocks: list[str] = []
        self._current: list[str] = []
        self._ignored_depth = 0
        self._in_title = False
        self._block_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag == "title":
            self._in_title = True
        if tag in self.BLOCK_TAGS:
            self._block_depth += 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._in_title:
            self._title_parts.append(data)
        if self._block_depth:
            self._current.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in self.IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if self._ignored_depth:
            return
        if tag == "title":
            self._in_title = False
            self.title = clean_text(" ".join(self._title_parts))
        if tag in self.BLOCK_TAGS and self._block_depth:
            self._block_depth -= 1
            if self._block_depth == 0:
                block = clean_text(" ".join(self._current))
                self._current = []
                if len(block) >= 80:
                    self._blocks.append(block)

    @property
    def text(self) -> str:
        return "\n".join(dict.fromkeys(self._blocks))


class PublicWebResearchClient:
    """Keyless research using public search results and direct page extraction."""

    search_endpoint = "https://html.duckduckgo.com/html/"

    def __init__(
        self,
        *,
        max_pages: int = 8,
        results_per_query: int = 5,
        timeout_seconds: int = 15,
    ) -> None:
        self.max_pages = max_pages
        self.results_per_query = results_per_query
        self.timeout_seconds = timeout_seconds

    def research(self, question: str) -> LiveResearchResult:
        plan = build_research_plan(question)
        queries = plan.queries[:4]
        actions: list[str] = []
        candidates: list[SearchResult] = []
        seen_urls: set[str] = set()

        for query in queries:
            actions.append(f"search: {query}")
            for result in self._search(query):
                canonical = canonical_url(result.url)
                if canonical in seen_urls:
                    continue
                seen_urls.add(canonical)
                candidates.append(
                    SearchResult(result.title, canonical, result.snippet)
                )
                if len(candidates) >= self.max_pages * 2:
                    break

        pages = self._fetch_pages(candidates[: self.max_pages * 2], actions)
        pages = pages[: self.max_pages]
        if not pages:
            pages = [
                PageContent(
                    title=result.title,
                    url=result.url,
                    text=result.snippet,
                )
                for result in candidates[: self.max_pages]
                if len(result.snippet) >= 80
            ]
            actions.extend(f"search_snippet: {page.url}" for page in pages)
        if not pages:
            raise LiveResearchError(
                "Search returned no readable pages or useful result summaries. "
                "Try a more specific query or run again."
            )

        return self._build_report(question, queries, pages, actions)

    def answer(self, question: str, *, depth: str = "brief") -> LiveResearchResult:
        actions = [f"search: {question}"]
        candidates = deduplicate_results(self._search(question))
        pages = self._fetch_pages(candidates[:6], actions)
        if not pages:
            pages = [
                PageContent(result.title, result.url, result.snippet)
                for result in candidates
                if len(result.snippet) >= 60
            ][:4]
        if not pages:
            raise LiveResearchError("No readable sources were found for this question.")
        return self._build_adaptive_answer(question, pages, actions, depth)

    def _search(self, query: str) -> list[SearchResult]:
        body = urllib.parse.urlencode({"q": query}).encode("utf-8")
        request = urllib.request.Request(
            self.search_endpoint,
            data=body,
            headers={"User-Agent": USER_AGENT},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                content = response.read(1_500_000).decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as error:
            raise LiveResearchError(f"Public web search failed: {error}") from error

        parser = SearchResultsParser()
        parser.feed(content)
        if parser.results:
            return parser.results[: self.results_per_query]
        return self._search_brave(query)

    def _search_brave(self, query: str) -> list[SearchResult]:
        url = "https://search.brave.com/search?" + urllib.parse.urlencode(
            {"q": query, "source": "web"}
        )
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                content = response.read(2_500_000).decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as error:
            raise LiveResearchError(
                f"Both public search providers failed: {error}"
            ) from error

        parser = BraveSearchParser()
        parser.feed(content)
        unique: list[SearchResult] = []
        seen_urls: set[str] = set()
        for result in parser.results:
            if result.url in seen_urls:
                continue
            seen_urls.add(result.url)
            unique.append(result)
            if len(unique) >= self.results_per_query:
                break
        return unique

    def _fetch_pages(
        self, candidates: list[SearchResult], actions: list[str]
    ) -> list[PageContent]:
        pages_by_url: dict[str, PageContent] = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_result = {
                executor.submit(self._fetch_page, result): result for result in candidates
            }
            for future in as_completed(future_to_result):
                result = future_to_result[future]
                try:
                    page = future.result()
                except (urllib.error.URLError, TimeoutError, ValueError):
                    continue
                if page:
                    pages_by_url[result.url] = page
                    actions.append(f"open_page: {result.url}")

        return [
            pages_by_url[result.url]
            for result in candidates
            if result.url in pages_by_url
        ]

    def _fetch_page(self, result: SearchResult) -> PageContent | None:
        try:
            page = self._fetch_direct(result)
            if page:
                return page
        except (urllib.error.URLError, TimeoutError, ValueError):
            pass
        return self._fetch_through_reader(result)

    def _fetch_direct(self, result: SearchResult) -> PageContent | None:
        request = urllib.request.Request(
            result.url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "application/xhtml+xml"}:
                return None
            raw = response.read(2_000_000)
            charset = response.headers.get_content_charset() or "utf-8"
        parser = ArticleParser()
        parser.feed(raw.decode(charset, errors="replace"))
        if len(parser.text) < 250:
            return None
        return PageContent(
            title=parser.title or result.title,
            url=result.url,
            text=parser.text,
        )

    def _fetch_through_reader(self, result: SearchResult) -> PageContent | None:
        reader_url = "https://r.jina.ai/http://" + result.url.split("://", 1)[-1]
        request = urllib.request.Request(
            reader_url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/plain"},
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds + 10
            ) as response:
                text = response.read(2_000_000).decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError):
            return None
        if len(text) < 250:
            return None
        title_match = re.search(r"^Title:\s*(.+)$", text, flags=re.MULTILINE)
        content_marker = "Markdown Content:"
        if content_marker in text:
            text = text.split(content_marker, 1)[1].strip()
        return PageContent(
            title=clean_text(title_match.group(1)) if title_match else result.title,
            url=result.url,
            text=text,
        )

    def _build_report(
        self,
        question: str,
        queries: tuple[str, ...],
        pages: list[PageContent],
        actions: list[str],
    ) -> LiveResearchResult:
        terms = meaningful_terms(question)
        report_parts: list[str] = []
        citations: list[Citation] = []
        sources: list[SearchResult] = []

        def append(text: str) -> None:
            report_parts.append(text)

        def cite(index: int, page: PageContent) -> None:
            marker = f"[{index}]"
            start = sum(len(part) for part in report_parts)
            append(marker)
            citations.append(
                Citation(
                    start_index=start,
                    end_index=start + len(marker),
                    title=page.title,
                    url=page.url,
                )
            )

        append("DEEP RESEARCH REPORT\n\n")
        append("Executive summary\n")
        append(
            f"GYAAAN searched {len(queries)} complementary query angles and retrieved "
            f"{len(pages)} independent web sources. The report below extracts the "
            "passages most relevant to the question and keeps each finding attached "
            "to the page it came from.\n\n"
        )
        append(f"Research question\n{question}\n\n")
        append("Key findings from retrieved websites\n\n")

        all_passages: list[str] = []
        for index, page in enumerate(pages, start=1):
            passages = select_passages(page.text, terms, limit=3)
            if not passages:
                continue
            summary = " ".join(passages)
            all_passages.extend(passages)
            append(f"{index}. {page.title}\n")
            append(summary + " ")
            cite(index, page)
            append("\n\n")
            sources.append(
                SearchResult(title=page.title, url=page.url, snippet=summary[:300])
            )

        recurring = recurring_terms(all_passages, terms)
        append("Cross-source comparison\n")
        if recurring:
            append(
                "Recurring concepts across the retrieved material include: "
                + ", ".join(recurring)
                + ". This indicates where multiple pages overlap, but repetition "
                "alone does not prove that a claim is correct.\n\n"
            )
        append(
            "The source sections above are kept separate so disagreements and "
            "differences in scope remain visible. Follow the citation links to "
            "inspect the original context before making an important decision.\n\n"
        )
        append("Limitations\n")
        append(
            "This keyless mode uses public search pages and local text extraction. "
            "Some websites block automated access, dynamic content may be missing, "
            "and this report uses extractive synthesis rather than a hosted language "
            "model. Treat it as a research starting point, not a substitute for "
            "professional review."
        )

        return LiveResearchResult(
            answer="".join(report_parts),
            sources=sources,
            citations=citations,
            actions=actions,
        )

    def _build_adaptive_answer(
        self,
        question: str,
        pages: list[PageContent],
        actions: list[str],
        depth: str,
    ) -> LiveResearchResult:
        office_holder = extract_office_holder_answer(question, pages)
        if depth == "brief" and office_holder:
            text, page = office_holder
            marker = "[1]"
            answer = f"{text} {marker}"
            return LiveResearchResult(
                answer=answer,
                sources=[
                    SearchResult(
                        title=page.title,
                        url=page.url,
                        snippet=text,
                    )
                ],
                citations=[
                    Citation(
                        start_index=len(answer) - len(marker),
                        end_index=len(answer),
                        title=page.title,
                        url=page.url,
                    )
                ],
                actions=actions,
            )

        terms = meaningful_terms(question)
        passage_limit = {"brief": 1, "standard": 2, "detailed": 3}.get(depth, 2)
        source_limit = {"brief": 3, "standard": 5, "detailed": 8}.get(depth, 5)
        selected: list[tuple[PageContent, list[str]]] = []
        for page in pages[:source_limit]:
            passages = select_passages(page.text, terms, limit=passage_limit)
            if passages:
                selected.append((page, passages))
        if not selected:
            raise LiveResearchError("Sources were found, but no relevant passages could be extracted.")

        answer_parts: list[str] = []
        citations: list[Citation] = []
        sources: list[SearchResult] = []

        def append(value: str) -> None:
            answer_parts.append(value)

        def add_citation(index: int, page: PageContent) -> None:
            marker = f"[{index}]"
            start = sum(len(part) for part in answer_parts)
            append(marker)
            citations.append(
                Citation(start, start + len(marker), page.title, page.url)
            )

        if depth == "brief":
            append(selected[0][1][0] + " ")
            add_citation(1, selected[0][0])
            if len(selected) > 1:
                append("\n\nAlso useful: " + selected[1][1][0] + " ")
                add_citation(2, selected[1][0])
        else:
            append("Answer\n")
            append(selected[0][1][0] + " ")
            add_citation(1, selected[0][0])
            append("\n\nKey details\n")
            for index, (page, passages) in enumerate(selected, start=1):
                append(f"{index}. {' '.join(passages)} ")
                add_citation(index, page)
                append("\n")

        for page, passages in selected:
            sources.append(
                SearchResult(
                    title=page.title,
                    url=page.url,
                    snippet=" ".join(passages)[:300],
                )
            )
        return LiveResearchResult(
            answer="".join(answer_parts).strip(),
            sources=sources,
            citations=citations,
            actions=actions,
        )


def unwrap_duckduckgo_url(href: str) -> str:
    href = html.unescape(href)
    if href.startswith("//"):
        href = "https:" + href
    parsed = urllib.parse.urlparse(href)
    if parsed.netloc.endswith("duckduckgo.com"):
        target = urllib.parse.parse_qs(parsed.query).get("uddg", [""])[0]
        href = urllib.parse.unquote(target)
    parsed = urllib.parse.urlparse(href)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return href


def canonical_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.query, "")
    )


def deduplicate_results(results: list[SearchResult]) -> list[SearchResult]:
    unique: list[SearchResult] = []
    seen: set[str] = set()
    for result in results:
        url = canonical_url(result.url)
        if url in seen:
            continue
        seen.add(url)
        unique.append(SearchResult(result.title, url, result.snippet))
    return unique


def extract_office_holder_answer(
    question: str, pages: list[PageContent]
) -> tuple[str, PageContent] | None:
    lowered = question.lower()
    if not any(
        marker in lowered
        for marker in ("cm of", "chief minister of", "who is the cm", "who is chief minister")
    ):
        return None

    place_match = re.search(
        r"(?:cm|chief minister)\s+of\s+(.+?)(?:\?|$)",
        question,
        flags=re.IGNORECASE,
    )
    place = clean_text(place_match.group(1)) if place_match else "the state"

    for page in pages:
        text = clean_text(page.text)
        incumbent = re.search(
            r"Incumbent\s+([A-Z][A-Za-z .'-]{2,60}?)\s+since\s+"
            r"(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})",
            text,
        )
        if not incumbent:
            continue
        name = incumbent.group(1).strip()
        date = incumbent.group(2)
        year = date.rsplit(" ", 1)[-1]
        details = [f"{name} is the Chief Minister of {place}", f"in office since {date}"]

        party = None
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            relevant = name in sentence or (
                year in sentence and "election" in sentence.lower()
            )
            if not relevant:
                continue
            if "Bharatiya Janata Party" in sentence:
                party = "Bharatiya Janata Party (BJP)"
                break
            if "All India Trinamool Congress" in sentence:
                party = "All India Trinamool Congress (TMC)"
                break
        if party:
            details.append(f"and belongs to the {party}")

        if re.search(
            rf"{year} (?:West Bengal )?(?:Legislative Assembly|assembly) election",
            text,
            flags=re.IGNORECASE,
        ):
            details.append(f"following the {year} Assembly election")

        return ", ".join(details) + ".", page
    return None


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def meaningful_terms(value: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]{3,}", value.lower())
        if word not in STOP_WORDS
    }


def select_passages(text: str, terms: set[str], limit: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", clean_text(text))
    scored: list[tuple[float, int, str]] = []
    for position, sentence in enumerate(sentences):
        if not 70 <= len(sentence) <= 500:
            continue
        words = set(re.findall(r"[a-z0-9]{3,}", sentence.lower()))
        overlap = len(words & terms)
        score = overlap * 4 + min(len(sentence), 240) / 240
        if overlap or not terms:
            scored.append((score, -position, sentence))
    selected = sorted(scored, reverse=True)[:limit]
    return [sentence for _, _, sentence in sorted(selected, key=lambda item: -item[1])]


def recurring_terms(passages: list[str], query_terms: set[str]) -> list[str]:
    counts: dict[str, int] = {}
    for passage in passages:
        for word in set(re.findall(r"[a-z][a-z0-9-]{3,}", passage.lower())):
            if word in STOP_WORDS or word in query_terms:
                continue
            counts[word] = counts.get(word, 0) + 1
    return [
        word
        for word, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if count >= 2
    ][:10]
