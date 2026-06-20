# GYAAAN

GYAAAN is an adaptive assistant with optional deep web research.

## Product Direction

GYAAAN is designed to avoid arbitrary product-level chat quotas. The local app
does not impose a message counter or daily chat cap. Real throughput is still
limited by hardware, network access, website availability, and any optional
provider's own quota.

Answer length adapts to intent:

- Direct factual question: answer first, then one or two useful details.
- Normal explanatory question: concise explanation with clear ordering.
- Explicit "detailed", "in depth", or Deep Research request: expanded analysis.

The browser streams the answer progressively from start to finish instead of
waiting and replacing the entire response at once.

## Run

```bash
python3 app.py "What is the latest news about AI models?" --trace
```

Example without web search:

```bash
python3 app.py "Explain binary search in simple words" --trace
```

Example with the coding role:

```bash
python3 app.py "Write Python code for a simple calculator" --trace
```

## Deep Research

Use `--deep-research` (or `--deep`) when a question needs broader search,
comparison, and source checking:

```bash
python3 app.py \
  "Search for the best restaurants in Connaught Place" \
  --deep-research --trace
```

Deep Research:

1. Searches the public web from several complementary angles.
2. Opens multiple result pages and extracts their readable text.
3. Selects passages relevant to the question and builds a cited report locally.
4. Returns clickable websites and a trace of searches and opened pages.

No API key is required. This keyless mode is extractive: it summarizes retrieved
passages without pretending to have the reasoning quality of a hosted model.
Sites that block automated access may be skipped.

An optional OpenAI provider remains available by setting
`GYAAN_RESEARCH_PROVIDER=openai` and `OPENAI_API_KEY`.

## Browser Interface

```bash
python3 app.py --serve
```

Then open `http://127.0.0.1:8000`.

Quick adaptive answers are the default. Enable **Deep Research** only when a
question needs broad multi-source investigation.

## Deploy To Vercel

Deploy the `gyaan/` directory as the Vercel project root. The app includes:

- `api/index.py`: Vercel Python runtime entrypoint.
- `vercel.json`: rewrites the home page and API requests to the Python handler.
- `.python-version`: pins the deployment runtime to Python 3.12.

From this directory:

```bash
vercel
vercel --prod
```

For optional hosted AI research, set these environment variables in Vercel:

```text
OPENAI_API_KEY=<set this in the Vercel dashboard only>
GYAAN_RESEARCH_PROVIDER=openai
GYAAN_RESEARCH_MODEL=gpt-5.5
```

Without those variables, GYAAAN still runs in the default keyless public-web
mode. Some websites may block automated fetches, so deploy logs are useful when
debugging deep-research failures.

## Project Structure

```text
gyaan/
├─ app.py
├─ api/
│  └─ index.py       # Vercel Python function entrypoint
├─ vercel.json       # Vercel routes and function config
├─ gyaan/
│  ├─ config.py       # environment-backed settings
│  ├─ router.py       # decides web/no-web and model roles
│  ├─ research.py     # plans complementary deep-research searches
│  ├─ web_search.py   # search interface + offline demo client
│  ├─ models.py       # model interface + demo specialist roles
│  ├─ mixer.py        # vivek3.0 final mixing layer
│  ├─ pipeline.py     # end-to-end orchestration
│  └─ providers/      # placeholders for real API adapters
├─ prompts/           # editable prompt files
├─ config/            # default project config
├─ examples/          # sample user questions
├─ tests/             # unit tests
├─ scripts/           # local run/check helpers
├─ docs/              # architecture and roadmap
├─ .env.example
├─ requirements.txt
└─ README.md
```

## What To Show In Code

- `gyaan/router.py`: proves the app routes fresh/current questions to search.
- `gyaan/models.py`: shows different model roles.
- `gyaan/mixer.py`: shows `vivek3.0`, the final model-mixing layer.
- `gyaan/pipeline.py`: shows the full flow from question to final answer.

## Production Upgrade Points

Replace:

- `DemoWebSearchClient` with a real provider such as Tavily, SerpAPI, Brave Search, or Bing.
- `DemoModelClient` with real model calls such as OpenAI, Gemini, Claude, or a local model.

Keep the same pipeline shape so the architecture stays understandable.
