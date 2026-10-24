# ============================================================================
#  TOOLS  -  tools.py
# ----------------------------------------------------------------------------
#  A "tool" is a small function the AI is ALLOWED to call when it decides it
#  needs help. The AI itself can't browse the web or write files - but it can
#  ask these tools to do it. Each tool has:
#     - a name        (how the AI refers to it)
#     - a function    (the actual Python code that runs)
#     - a description (plain English telling the AI WHEN to use it)
#  The AI reads the description to decide which tool fits the task.
#
#  NOTE: This uses LangChain 1.x style. For your OWN function, the easy way to
#  make a tool is the @tool decorator. Prebuilt tools (search, Wikipedia) are
#  ALREADY tools, so we just use them directly - no need to wrap them.
# ============================================================================

# Ready-made tools that the LangChain community already built for us:
from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper

# @tool turns a plain Python function into a tool the AI can call.
from langchain_core.tools import tool

from datetime import datetime   # used to timestamp saved files

# --- Wikipedia setup (fixes HTTP 429 "too many requests") ---------------
# The underlying 'wikipedia' package ships with a generic, shared User-Agent
# that Wikipedia now rate-limits. Wikipedia's API policy asks every app to send
# its OWN descriptive User-Agent, so we set one here. We also switch the API
# URL to https. (Do this BEFORE any Wikipedia lookup happens.)
import wikipedia.wikipedia as _wiki
_wiki.USER_AGENT = "ai-agent-learning-project/1.0 (educational use)"
_wiki.API_URL = "https://en.wikipedia.org/w/api.php"


# ---------------------------------------------------------------------------
# TOOL 1 - SAVE TO A TEXT FILE  (our own custom tool)
# ---------------------------------------------------------------------------
# The @tool decorator above the function is all it takes to make it a tool.
# IMPORTANT: the text in the triple-quoted """docstring""" IS the description
# the AI reads to decide when to use this tool - so write it clearly.
@tool
def save_text_to_file(data: str) -> str:
    """Saves structured research data to a local text file (research_output.txt)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_text = f"--- Research Output ---\nTimestamp: {timestamp}\n\n{data}\n\n"

    # "a" mode = append (add to the end of the file; don't overwrite what's there).
    with open("research_output.txt", "a", encoding="utf-8") as f:
        f.write(formatted_text)

    # Whatever we return here is given back to the AI so it knows it worked.
    return "Data successfully saved to research_output.txt"

# Give it the simple name 'save_tool' so main.py can import it.
save_tool = save_text_to_file


# ---------------------------------------------------------------------------
# TOOL 2 - WEB SEARCH (DuckDuckGo)
# ---------------------------------------------------------------------------
# DuckDuckGoSearchRun() is a prebuilt tool - already ready to hand to the agent.
# (No API key needed.) Needs the 'ddgs' package installed.
search_tool = DuckDuckGoSearchRun()


# ---------------------------------------------------------------------------
# TOOL 3 - WIKIPEDIA LOOKUP
# ---------------------------------------------------------------------------
# WikipediaAPIWrapper settings:
#   top_k_results=1        -> return only the single best matching article
#   doc_content_chars_max  -> cut the article text to this many characters
#                             (100 is tiny - raise it, e.g. 1000, for more detail)
api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=100)
wiki_tool = WikipediaQueryRun(api_wrapper=api_wrapper)
