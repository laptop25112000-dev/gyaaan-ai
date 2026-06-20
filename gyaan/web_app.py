import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .pipeline import GyaanPipeline


PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GYAAAN</title>
  <style>
    * { box-sizing: border-box; }
    :root {
      color-scheme: dark;
      --bg: #101214;
      --panel: #181a1d;
      --panel-2: #202327;
      --line: #30343a;
      --text: #f2f2ed;
      --muted: #a5a69f;
      --accent: #b8f36b;
      --accent-dark: #26351a;
      --composer-gutter: 18px;
    }
    html { height: 100%; }
    body {
      margin: 0; min-height: 100vh; min-height: 100dvh; overflow: hidden;
      background: var(--bg); color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
    }
    button, textarea { font: inherit; }
    button { color: inherit; }
    .app { display: grid; grid-template-columns: 260px minmax(0, 1fr); height: 100vh; height: 100dvh; }
    aside {
      border-right: 1px solid var(--line); background: #0d0e0c;
      padding: 14px; display: flex; flex-direction: column;
      min-height: 0;
    }
    .brand {
      display: flex; align-items: center; gap: 10px; padding: 8px 8px 18px;
      font-size: 15px; font-weight: 750; letter-spacing: .04em;
    }
    .mark {
      width: 28px; height: 28px; display: grid; place-items: center;
      border-radius: 8px; background: var(--accent); color: #151a10; font-weight: 900;
    }
    .new-chat, .history-item {
      width: 100%; border: 1px solid var(--line); border-radius: 8px;
      background: transparent; padding: 11px 12px; text-align: left; cursor: pointer;
    }
    .new-chat:hover, .history-item:hover { background: var(--panel); }
    .history-label {
      color: #74766f; font-size: 11px; font-weight: 700; margin: 24px 9px 8px;
      text-transform: uppercase; letter-spacing: .08em;
    }
    .history { display: grid; gap: 5px; overflow: auto; }
    .history-item { border-color: transparent; color: #c8c9c2; white-space: nowrap;
      overflow: hidden; text-overflow: ellipsis; }
    .sidebar-foot { margin-top: auto; padding: 10px 8px; color: #777970; font-size: 12px; }
    main { min-width: 0; height: 100vh; height: 100dvh; min-height: 0; display: flex; flex-direction: column; }
    header {
      height: 58px; flex: 0 0 58px; display: flex; align-items: center;
      justify-content: space-between; padding: 0 22px; border-bottom: 1px solid var(--line);
      min-width: 0;
    }
    .title { font-weight: 650; font-size: 14px; }
    .mode-badge {
      color: var(--accent); background: var(--accent-dark); border: 1px solid #435e2c;
      border-radius: 999px; padding: 6px 10px; font-size: 12px; font-weight: 700;
    }
    .scroll { flex: 1; min-height: 0; overflow-y: auto; }
    .content { width: min(820px, calc(100% - 36px)); margin: 0 auto; padding: 50px 0 200px; }
    .hero { min-height: 55vh; min-height: 55dvh; display: grid; place-content: center; text-align: center; }
    .hero-symbol {
      margin: 0 auto 22px; width: 54px; height: 54px; border-radius: 8px;
      display: grid; place-items: center; background: var(--accent); color: #17200f;
      font-size: 24px; font-weight: 900;
    }
    h1 { margin: 0; font-size: 44px; letter-spacing: 0; }
    .hero p { color: var(--muted); margin: 12px auto 28px; max-width: 570px; line-height: 1.55; }
    .suggestions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .suggestion {
      border: 1px solid var(--line); background: var(--panel); border-radius: 8px;
      min-height: 58px; padding: 13px 14px; text-align: left; cursor: pointer;
      color: #d8d9d2; line-height: 1.3;
    }
    .suggestion:hover { border-color: #565950; background: var(--panel-2); }
    .message { margin-bottom: 28px; }
    .user-message {
      margin-left: auto; max-width: min(75%, 640px); width: fit-content; padding: 13px 16px;
      background: #292b27; border-radius: 8px 8px 4px 8px; line-height: 1.5;
      overflow-wrap: anywhere;
    }
    .research-head { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; min-width: 0; }
    .research-head .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--accent); }
    .research-head strong { font-size: 15px; }
    .research-head span { color: var(--muted); font-size: 13px; }
    .progress-card, .plan-card, .sources-card {
      border: 1px solid var(--line); background: var(--panel); border-radius: 8px;
      padding: 17px; margin: 12px 0;
    }
    .progress-row {
      display: flex; gap: 12px; align-items: center; padding: 8px 0; color: var(--muted);
      font-size: 14px;
    }
    .progress-row.active { color: var(--text); }
    .progress-row.done { color: #c9e9a5; }
    .status-icon { width: 18px; text-align: center; }
    .spinner {
      display: inline-block; width: 14px; height: 14px; border: 2px solid #53564e;
      border-top-color: var(--accent); border-radius: 50%; animation: spin .8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .section-label {
      margin: 0 0 12px; color: var(--muted); font-size: 12px; font-weight: 750;
      text-transform: uppercase; letter-spacing: .08em;
    }
    .chips { display: flex; flex-wrap: wrap; gap: 8px; }
    .chip { padding: 7px 10px; border-radius: 8px; background: #292b27; font-size: 12px; color: #c5c7bf; overflow-wrap: anywhere; }
    .report { padding: 14px 2px; line-height: 1.72; color: #e8e9e3; }
    .report h2 { margin: 12px 0; font-size: 24px; letter-spacing: 0; }
    .report-text { white-space: pre-wrap; overflow-wrap: anywhere; }
    .report-text a { color: #b8f36b; text-decoration: underline; text-underline-offset: 3px; }
    .source-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .source {
      display: block; color: inherit; text-decoration: none;
      min-width: 0; padding: 12px; border-radius: 8px; background: #252723;
      border: 1px solid #333630;
    }
    .source:hover { border-color: #648c42; background: #292c26; }
    .source-title { font-size: 13px; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .source-url { color: #8fa86f; font-size: 11px; margin-top: 5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    details { margin-top: 16px; color: var(--muted); }
    details pre { white-space: pre-wrap; font-size: 12px; line-height: 1.55; }
    .composer-wrap {
      position: fixed; left: 260px; right: 0; bottom: 0;
      padding: 20px var(--composer-gutter) calc(26px + env(safe-area-inset-bottom));
      background: linear-gradient(transparent, var(--bg) 28%);
    }
    .composer {
      width: min(820px, 100%); margin: auto; border: 1px solid #41433d;
      background: #20211f; border-radius: 8px; padding: 12px; box-shadow: 0 15px 50px #0008;
    }
    textarea {
      display: block; width: 100%; min-height: 54px; max-height: 180px; resize: none;
      border: 0; outline: 0; background: transparent; color: var(--text); padding: 5px 7px;
      line-height: 1.45;
    }
    textarea::placeholder { color: #85877f; }
    .composer-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 7px; }
    .controls { display: flex; gap: 7px; }
    .control {
      border: 1px solid #42453e; background: transparent; border-radius: 8px;
      padding: 7px 10px; font-size: 12px; cursor: pointer;
    }
    .control.selected { border-color: #648c42; color: var(--accent); background: var(--accent-dark); }
    .send {
      border: 0; width: 35px; height: 35px; border-radius: 50%;
      background: var(--accent); color: #141a10; font-size: 18px; font-weight: 900; cursor: pointer;
    }
    .send:disabled { opacity: .4; cursor: wait; }
    .disclaimer { text-align: center; color: #6f716a; font-size: 10px; margin-top: 9px; }
    .mobile-menu { display: none; }
    @media (max-width: 920px) {
      .app { grid-template-columns: 220px minmax(0, 1fr); }
      .composer-wrap { left: 220px; }
      .content { width: min(760px, calc(100% - 28px)); }
      .user-message { max-width: 84%; }
    }
    @media (max-width: 720px) {
      .app { grid-template-columns: 1fr; }
      aside { display: none; }
      header { height: 52px; flex-basis: 52px; padding: 0 14px; }
      .composer-wrap { left: 0; padding: 12px 12px calc(13px + env(safe-area-inset-bottom)); }
      .content { width: calc(100% - 24px); padding: 24px 0 190px; }
      .hero { min-height: auto; place-content: start; padding-top: 22px; }
      .hero-symbol { width: 44px; height: 44px; margin-bottom: 16px; font-size: 20px; }
      h1 { font-size: 32px; }
      .hero p { margin-bottom: 18px; font-size: 14px; }
      .suggestions, .source-grid { grid-template-columns: 1fr; }
      .user-message { max-width: 92%; }
      .progress-card, .plan-card, .sources-card { padding: 14px; }
      .composer-foot { align-items: flex-end; gap: 10px; }
      .controls { min-width: 0; flex-wrap: wrap; }
      .control { padding: 7px 9px; }
      .send { flex: 0 0 35px; }
      .disclaimer { display: none; }
      .mobile-menu { display: block; }
    }
    @media (max-width: 380px) {
      .mode-badge { padding: 5px 8px; font-size: 11px; }
      .suggestion { min-height: 52px; padding: 11px 12px; }
      .control { font-size: 11px; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <div class="brand"><span class="mark">G</span> GYAAAN</div>
      <button class="new-chat" onclick="resetChat()">+ New chat</button>
      <div class="history-label">Recent</div>
      <div class="history" id="history"></div>
      <div class="sidebar-foot">Adaptive answers. No artificial chat cap.</div>
    </aside>
    <main>
      <header>
        <div class="title">GYAAAN</div>
        <div class="mode-badge" id="modeBadge">Adaptive</div>
      </header>
      <div class="scroll" id="scroll">
        <div class="content" id="content">
          <div class="hero" id="hero">
            <div>
              <div class="hero-symbol">G</div>
              <h1>How can I help?</h1>
              <p>GYAAAN keeps direct questions brief, expands when you ask for detail, and can run deeper web research when needed.</p>
              <div class="suggestions">
                <button class="suggestion" onclick="usePrompt(this)">Who is the CM of West Bengal?</button>
                <button class="suggestion" onclick="usePrompt(this)">Explain binary search briefly</button>
                <button class="suggestion" onclick="usePrompt(this)">Explain quantum computing in detail</button>
                <button class="suggestion" onclick="usePrompt(this)">Compare electric car costs over five years</button>
              </div>
            </div>
          </div>
          <div id="conversation"></div>
        </div>
      </div>
      <div class="composer-wrap">
        <div class="composer">
          <textarea id="question" placeholder="Message GYAAAN..." rows="1"></textarea>
          <div class="composer-foot">
            <div class="controls">
              <button class="control" id="deepButton" onclick="toggleDeep()">Deep Research</button>
              <button class="control" id="traceButton" onclick="toggleTrace()">Trace</button>
            </div>
            <button class="send" id="send" onclick="submitResearch()">&#8593;</button>
          </div>
        </div>
        <div class="disclaimer">No artificial message cap. Actual capacity depends on your machine, network, and selected providers.</div>
      </div>
    </main>
  </div>
  <script>
    const question = document.getElementById("question");
    const conversation = document.getElementById("conversation");
    const hero = document.getElementById("hero");
    const scroll = document.getElementById("scroll");
    let deep = false;
    let trace = false;

    question.addEventListener("keydown", event => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        submitResearch();
      }
    });
    question.addEventListener("input", () => {
      question.style.height = "auto";
      question.style.height = Math.min(question.scrollHeight, 180) + "px";
    });

    function toggleDeep() {
      deep = !deep;
      document.getElementById("deepButton").classList.toggle("selected", deep);
      document.getElementById("modeBadge").textContent = deep ? "Deep Research" : "Adaptive";
    }
    function toggleTrace() {
      trace = !trace;
      document.getElementById("traceButton").classList.toggle("selected", trace);
    }
    function usePrompt(button) {
      question.value = button.textContent;
      question.focus();
    }
    function resetChat() {
      conversation.innerHTML = "";
      hero.style.display = "";
      question.value = "";
      question.focus();
    }
    function esc(value) {
      const node = document.createElement("div");
      node.textContent = value == null ? "" : String(value);
      return node.innerHTML;
    }
    function saveHistory(text) {
      const item = document.createElement("button");
      item.className = "history-item";
      item.textContent = text;
      document.getElementById("history").prepend(item);
    }
    function progressMarkup(turnId) {
      const labels = deep
        ? ["Understanding your question", "Building a research plan", "Searching multiple angles", "Checking evidence and conflicts", "Writing the report"]
        : ["Understanding your question", "Checking relevant sources", "Writing the right-sized answer"];
      return `<div class="progress-card" id="progressCard-${turnId}">${labels.map((label, index) =>
        `<div class="progress-row ${index === 0 ? "active" : ""}" data-step="${index}">
          <span class="status-icon">${index === 0 ? '<span class="spinner"></span>' : '&#9675;'}</span>
          <span>${label}</span>
        </div>`).join("")}</div>`;
    }
    function animateProgress(turnId) {
      const rows = [...document.querySelectorAll(`#progressCard-${turnId} .progress-row`)];
      let current = 0;
      return setInterval(() => {
        if (current < rows.length - 1) {
          rows[current].className = "progress-row done";
          rows[current].querySelector(".status-icon").innerHTML = "&#10003;";
          current += 1;
          rows[current].className = "progress-row active";
          rows[current].querySelector(".status-icon").innerHTML = '<span class="spinner"></span>';
        }
      }, 550);
    }
    function completeProgress(turnId) {
      document.querySelectorAll(`#progressCard-${turnId} .progress-row`).forEach(row => {
        row.className = "progress-row done";
        row.querySelector(".status-icon").innerHTML = "&#10003;";
      });
    }
    async function submitResearch() {
      const text = question.value.trim();
      if (!text) return;
      const turnId = Date.now().toString();
      hero.style.display = "none";
      document.getElementById("send").disabled = true;
      conversation.insertAdjacentHTML("beforeend", `
        <div class="message user-message">${esc(text)}</div>
        <div class="message">
          <div class="research-head"><span class="dot"></span><strong>GYAAAN</strong><span>${deep ? "Deep research" : "Adaptive answer"}</span></div>
          ${progressMarkup(turnId)}
          <div id="result-${turnId}">
            <article class="report">
              <div class="report-text" id="reportText-${turnId}"></div>
            </article>
            <div id="resultMeta-${turnId}"></div>
          </div>
        </div>`);
      question.value = "";
      saveHistory(text);
      scroll.scrollTop = scroll.scrollHeight;
      const timer = animateProgress(turnId);
      try {
        const response = await fetch("/api/chat-stream", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({question: text, deep, trace})
        });
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || "Request failed");
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalData = null;
        while (true) {
          const {value, done} = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, {stream: true});
          const lines = buffer.split("\n");
          buffer = lines.pop();
          for (const line of lines) {
            if (!line.trim()) continue;
            const event = JSON.parse(line);
            if (event.type === "delta") {
              document.getElementById(`reportText-${turnId}`).append(
                document.createTextNode(event.text)
              );
              scroll.scrollTop = scroll.scrollHeight;
            } else if (event.type === "done") {
              finalData = event.data;
            } else if (event.type === "error") {
              throw new Error(event.error);
            }
          }
        }
        clearInterval(timer);
        completeProgress(turnId);
        if (finalData) {
          document.getElementById(`progressCard-${turnId}`).remove();
          renderResult(finalData, turnId);
        }
      } catch (error) {
        clearInterval(timer);
        document.getElementById(`result-${turnId}`).innerHTML =
          `<div class="plan-card">Could not complete research: ${esc(error.message)}</div>`;
      } finally {
        document.getElementById("send").disabled = false;
        scroll.scrollTop = scroll.scrollHeight;
      }
    }
    function renderResult(data, turnId) {
      const plan = data.plan;
      const planHtml = plan ? `
        <div class="plan-card">
          <p class="section-label">Research plan</p>
          <div class="chips">${plan.queries.map(query => `<span class="chip">${esc(query)}</span>`).join("")}</div>
        </div>` : "";
      const sourcesHtml = data.sources.length ? `
        <div class="sources-card">
          <p class="section-label">${data.sources.length} websites cited</p>
          <div class="source-grid">${data.sources.map(source => `
            <a class="source" href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">
              <div class="source-title">${esc(source.title)}</div>
              <div class="source-url">${esc(source.url)}</div>
            </a>`).join("")}
          </div>
        </div>` : "";
      const actionsHtml = data.actions && data.actions.length ? `
        <details><summary>${data.actions.length} web research actions</summary><pre>${esc(data.actions.join("\n"))}</pre></details>` : "";
      const traceHtml = data.trace ? `
        <details><summary>View research trace</summary><pre>${esc(data.trace)}</pre></details>` : "";
      document.getElementById(`resultMeta-${turnId}`).innerHTML = `
        ${planHtml}
        ${sourcesHtml}
        ${actionsHtml}
        ${traceHtml}`;
      renderCitedReport(data.answer, data.citations || [], turnId);
    }
    function renderCitedReport(answer, citations, turnId) {
      const container = document.getElementById(`reportText-${turnId}`);
      container.innerHTML = "";
      const valid = citations
        .filter(citation =>
          Number.isInteger(citation.start_index) &&
          Number.isInteger(citation.end_index) &&
          citation.start_index >= 0 &&
          citation.end_index > citation.start_index &&
          citation.end_index <= answer.length)
        .sort((left, right) => left.start_index - right.start_index);
      let cursor = 0;
      valid.forEach(citation => {
        if (citation.start_index < cursor) return;
        container.append(document.createTextNode(answer.slice(cursor, citation.start_index)));
        const link = document.createElement("a");
        link.href = citation.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.title = citation.title;
        link.textContent = answer.slice(citation.start_index, citation.end_index);
        container.append(link);
        cursor = citation.end_index;
      });
      container.append(document.createTextNode(answer.slice(cursor)));
    }
  </script>
</body>
</html>
"""

MAX_REQUEST_BYTES = 1_000_000


class GyaanHandler(BaseHTTPRequestHandler):
    pipeline = GyaanPipeline(use_live_answers=True)

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self._send_html(PAGE)
            return
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self._send_json({"error": "Not found"}, status=404)

    def do_HEAD(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self._send_html(PAGE, include_body=False)
            return
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self._send_json({"error": "Not found"}, status=404, include_body=False)

    def do_POST(self) -> None:
        if self.path not in {"/api/research", "/api/chat-stream"}:
            self._send_json({"error": "Not found"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                self._send_json({"error": "Invalid request size"}, status=400)
                return

            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                self._send_json({"error": "Request body must be a JSON object"}, status=400)
                return

            question = str(payload.get("question", "")).strip()
            if not question:
                self._send_json({"error": "Question is required"}, status=400)
                return

            deep = payload.get("deep", False)
            trace = payload.get("trace", False)
            if not isinstance(deep, bool) or not isinstance(trace, bool):
                self._send_json(
                    {"error": "'deep' and 'trace' must be JSON booleans"},
                    status=400,
                )
                return

            run = self.pipeline.ask(question, deep_research=deep)
            plan = None
            if run.research_plan:
                plan = {
                    "queries": list(run.research_plan.queries),
                    "criteria": list(run.research_plan.evaluation_criteria),
                }
            response_payload = {
                    "question": question,
                    "mode": run.route.research_mode,
                    "depth": run.answer_policy.depth if run.answer_policy else "standard",
                    "answer": run.final.answer,
                    "provider": run.provider,
                    "plan": plan,
                    "sources": [
                        {
                            "title": source.title,
                            "url": source.url,
                            "snippet": source.snippet,
                        }
                        for source in run.search_results
                    ],
                    "citations": [
                        {
                            "start_index": citation.start_index,
                            "end_index": citation.end_index,
                            "title": citation.title,
                            "url": citation.url,
                        }
                        for citation in run.citations
                    ],
                    "actions": list(run.research_actions),
                    "trace": run.final.trace if trace else "",
                }
            if self.path == "/api/chat-stream":
                self._send_stream(response_payload)
            else:
                self._send_json(response_payload)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            self._send_json({"error": "Invalid request body"}, status=400)
        except Exception as error:
            self._send_json({"error": str(error)}, status=500)

    def _send_html(self, content: str, include_body: bool = True) -> None:
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def _send_json(
        self, payload: dict, status: int = 200, include_body: bool = True
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def _send_stream(self, payload: dict) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        answer = payload["answer"]
        for chunk in stream_chunks(answer):
            event = json.dumps({"type": "delta", "text": chunk}) + "\n"
            self.wfile.write(event.encode("utf-8"))
            self.wfile.flush()
        event = json.dumps({"type": "done", "data": payload}) + "\n"
        self.wfile.write(event.encode("utf-8"))
        self.wfile.flush()

    def log_message(self, format: str, *args: object) -> None:
        print(f"[web] {self.address_string()} - {format % args}")


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), GyaanHandler)
    print(f"GYAAAN web app running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def stream_chunks(text: str, target_size: int = 24):
    words = text.split(" ")
    chunk = ""
    for word in words:
        candidate = word if not chunk else f"{chunk} {word}"
        if len(candidate) >= target_size and chunk:
            yield chunk + " "
            chunk = word
        else:
            chunk = candidate
    if chunk:
        yield chunk
