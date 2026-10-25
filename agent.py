"""
Core of the AI research agent.

This module holds everything the agent needs (the model, the prompt, the tools
and the structured output shape) and exposes ONE function: research().

It is deliberately separate from the user interfaces so that both the command
line app (main.py) and the web app (app.py) share exactly the same logic
instead of each having their own copy.

HOW AN AGENT WORKS :
    A plain language model can only turn text into text. An "agent" is a model
    that has been given tools plus permission to decide when to call them. The
    loop is: think -> maybe call a tool -> read the result -> think again ->
    produce a final answer.
"""

from typing import Callable, Optional

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from tools import search_tool, wiki_tool, save_tool


# ---------------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------------
# Google's free tier regularly answers "503 high demand" when a model is busy.
# That is a capacity problem on Google's side, not a bug in this code, so we
# keep a list and fall through to the next model when one is overloaded.
MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
]


# ---------------------------------------------------------------------------
# OUTPUT SHAPE
# ---------------------------------------------------------------------------
# A raw model reply is free-form prose, which is awkward to build on. Declaring
# the shape with Pydantic means every answer arrives with the same four fields,
# already validated, so the UI layer can render it without guesswork.
class ResearchResponse(BaseModel):
    topic: str = Field(description="The subject that was researched")
    summary: str = Field(description="The findings, written as prose")
    sources: list[str] = Field(description="Where the information came from")
    tools_used: list[str] = Field(description="Which tools the agent called")


# ---------------------------------------------------------------------------
# PROMPT
# ---------------------------------------------------------------------------
# The system prompt is the agent's standing instruction set. It applies to
# every question, unlike the user's query which changes each turn.
SYSTEM_PROMPT = """
You are a research assistant that produces concise, well-sourced summaries.

Guidelines:
- Use the web search tool for current events and recent information.
- Use the Wikipedia tool for established facts, places, people and definitions.
- Always report the sources you actually relied on.
- Only call the save tool when the user explicitly asks to save the result.
"""

TOOLS = [search_tool, wiki_tool, save_tool]


def _classify_error(error: Exception) -> str:
    """Sort an API failure into 'busy', 'quota' or 'fatal'.

    'busy' and 'quota' are both worth retrying on a different model, because
    Google applies capacity and free-tier limits per model. 'fatal' covers real
    faults (a bad key, a malformed request) which must surface immediately
    rather than being hidden behind a fallback.
    """
    message = str(error)
    lowered = message.lower()

    if "503" in message or "UNAVAILABLE" in message:
        return "busy"
    if "429" in message or "RESOURCE_EXHAUSTED" in message or "quota" in lowered:
        return "quota"
    return "fatal"


def _run_single_model(model_name: str, query: str, api_key: Optional[str]) -> ResearchResponse:
    """Build an agent on one specific model and answer the query with it."""
    # max_retries=0 because we handle fallback ourselves. Leaving the library's
    # own retries on makes a busy model look like a frozen program: it quietly
    # retries with backoff for minutes instead of reporting the 503.
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        max_retries=0,
        google_api_key=api_key,  # None means "read GOOGLE_API_KEY from the environment"
    )

    # create_agent is the LangChain 1.x entry point. Passing response_format a
    # Pydantic class makes the agent return a ready-built ResearchResponse.
    agent = create_agent(
        model=llm,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        response_format=ResearchResponse,
    )

    result = agent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["structured_response"]


class AgentUnavailableError(RuntimeError):
    """Base class for 'the agent cannot answer right now, but nothing is broken'.

    Interfaces can catch this one type to show a calm message, rather than
    having to know about each individual cause.
    """


class AllModelsBusyError(AgentUnavailableError):
    """Every model reported that it was overloaded (HTTP 503)."""


class QuotaExceededError(AgentUnavailableError):
    """The API key has used up its allowance (HTTP 429)."""


def research(
    query: str,
    api_key: Optional[str] = None,
    on_status: Optional[Callable[[str], None]] = None,
) -> ResearchResponse:
    """Research `query` and return a validated ResearchResponse.

    Tries each model in MODELS in order, moving on when one is overloaded or
    out of quota. `on_status` is an optional callback used to report progress,
    so the caller decides how to display it (print to a terminal, draw in a web
    page, write to a log) without this module knowing anything about UIs.

    Raises:
        QuotaExceededError: the key's allowance is used up.
        AllModelsBusyError: every model was overloaded.
        Exception: any other failure is re-raised unchanged.
    """
    saw_quota_limit = False

    for model_name in MODELS:
        try:
            if on_status:
                on_status(f"Querying {model_name}...")
            return _run_single_model(model_name, query, api_key)
        except Exception as error:
            kind = _classify_error(error)

            if kind == "fatal":
                raise

            if kind == "quota":
                saw_quota_limit = True

            if on_status:
                reason = "out of quota" if kind == "quota" else "busy"
                on_status(f"{model_name} is {reason}, falling back to the next model...")
            continue

    # Quota is the more useful diagnosis when both occurred: waiting a minute
    # fixes an overloaded model, but not an exhausted allowance.
    if saw_quota_limit:
        raise QuotaExceededError(
            "The daily request allowance for this API key has been used up. "
            "Free-tier quota resets every 24 hours."
        )

    raise AllModelsBusyError(
        "Every model is currently overloaded. This is a temporary capacity "
        "limit on Google's side. Please try again in a minute."
    )
