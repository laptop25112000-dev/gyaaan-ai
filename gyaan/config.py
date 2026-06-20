import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mixer_model: str = "vivek3.0"
    search_provider: str = "demo"
    model_provider: str = "demo"
    max_sources: int = 3
    deep_research_sources: int = 12
    sources_per_research_query: int = 3
    show_debug_trace: bool = False
    openai_api_key: str = ""
    research_model: str = "gpt-5.5"
    research_max_tool_calls: int = 20
    research_provider: str = "public"


def load_settings() -> Settings:
    return Settings(
        mixer_model=os.getenv("GYAAN_MIXER_MODEL", "vivek3.0"),
        search_provider=os.getenv("GYAAN_SEARCH_PROVIDER", "demo"),
        model_provider=os.getenv("GYAAN_MODEL_PROVIDER", "demo"),
        max_sources=int(os.getenv("GYAAN_MAX_SOURCES", "3")),
        deep_research_sources=int(os.getenv("GYAAN_DEEP_RESEARCH_SOURCES", "12")),
        sources_per_research_query=int(
            os.getenv("GYAAN_SOURCES_PER_RESEARCH_QUERY", "3")
        ),
        show_debug_trace=os.getenv("GYAAN_DEBUG", "0") == "1",
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        research_model=os.getenv("GYAAN_RESEARCH_MODEL", "gpt-5.5"),
        research_max_tool_calls=int(
            os.getenv("GYAAN_RESEARCH_MAX_TOOL_CALLS", "20")
        ),
        research_provider=os.getenv("GYAAN_RESEARCH_PROVIDER", "public"),
    )
