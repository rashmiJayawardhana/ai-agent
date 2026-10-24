# ============================================================================
#  AI RESEARCH AGENT  -  main.py
# ----------------------------------------------------------------------------
#  WHAT THIS PROGRAM DOES :
#  You type a research question. An AI model (Google Gemini) answers it.
#  The AI is allowed to USE TOOLS to help itself:
#     - search the web (DuckDuckGo)
#     - look things up on Wikipedia
#     - save the final answer to a text file
#  Finally, we force the AI's answer into a tidy, predictable structure
#  (topic, summary, sources, tools_used) so our code can rely on it.
#
#  This kind of program - an LLM that can decide to call tools - is called
#  an "AI agent".
#
#  NOTE: This uses LangChain 1.x (the modern version). In LangChain 1.x the
#  whole agent setup is ONE function: create_agent(...). Older tutorials use
#  create_tool_calling_agent + AgentExecutor, which no longer exist.
# ============================================================================


# ---------------------------------------------------------------------------
# 1) IMPORTS  - bringing in code other people wrote so we don't rewrite it.
# ---------------------------------------------------------------------------

from dotenv import load_dotenv            # reads your .env file (where your API key lives)
from pydantic import BaseModel            # lets us define the "shape" of the answer we want

# This is the Google Gemini chat model wrapper from LangChain.
# LangChain is a library that gives every AI provider (Google, OpenAI,
# Anthropic...) the same easy-to-use interface.
from langchain_google_genai import ChatGoogleGenerativeAI

# create_agent is the modern (LangChain 1.x) way to build an agent in one call.
from langchain.agents import create_agent

# Our own tools, defined in the file tools.py.
from tools import search_tool, wiki_tool, save_tool


# ---------------------------------------------------------------------------
# 2) LOAD SECRETS
# ---------------------------------------------------------------------------
# load_dotenv() reads the .env file and loads things like
# GOOGLE_API_KEY into the program's environment so the AI library can find it.
# You do NOT write the key in this file - keep it in .env only (safer).
load_dotenv()


# ---------------------------------------------------------------------------
# 3) DEFINE THE SHAPE OF THE ANSWER WE WANT
# ---------------------------------------------------------------------------
# A normal AI reply is just free-form text. That's hard for code to use.
# Here we say: "I want the answer to always have these 4 fields."
# Pydantic (BaseModel) is a library that describes and checks data shapes.
class ResearchResponse(BaseModel):
    topic: str              # what the research was about
    summary: str            # the main findings, written out
    sources: list[str]      # a list of where the info came from
    tools_used: list[str]   # which tools the AI decided to use


# ---------------------------------------------------------------------------
# 4) CHOOSE THE AI MODELS (the "brain") - with automatic backups
# ---------------------------------------------------------------------------
# On the FREE tier, a model sometimes replies "503 high demand" (it's just
# busy right now - nothing wrong with your code). To handle that gracefully,
# we list several models. If the first is overloaded, the program automatically
# tries the next one. "flash" models are fast and cheap.
# (If you ever get a 404 "model not found", the name changed - see LEARN.md.)
MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
]


# ---------------------------------------------------------------------------
# 5) THE SYSTEM PROMPT (the AI's standing instructions)
# ---------------------------------------------------------------------------
# The "system prompt" is the AI's personality and rules - it applies to every
# question. Here we tell it to act as a research assistant and use its tools.
system_prompt = """
You are a research assistant that will help generate a research paper.
Answer the user query and use the available tools when they are helpful
(web search, Wikipedia, and saving results to a file).
"""


# The tools the AI is allowed to use. (They're defined in tools.py.)
tools = [search_tool, wiki_tool, save_tool]


# ---------------------------------------------------------------------------
# 6) A HELPER THAT BUILDS AND RUNS THE AGENT ON ONE MODEL
# ---------------------------------------------------------------------------
# We put the setup in a small function so we can easily call it again with a
# different model if the first one is busy.
def run_research(model_name: str, query: str):
    # ChatGoogleGenerativeAI connects to Gemini using GOOGLE_API_KEY from .env.
    # max_retries=0: don't silently retry a busy model - we handle fallback ourselves.
    llm = ChatGoogleGenerativeAI(model=model_name, max_retries=0)

    # create_agent wires everything together:
    #   - model          = the brain (Gemini)
    #   - tools          = the abilities it can choose to use
    #   - system_prompt  = its standing instructions
    #   - response_format= the shape we want the FINAL answer in. Because we pass
    #                      our ResearchResponse class here, LangChain automatically
    #                      fills in topic/summary/sources/tools_used and hands us
    #                      back a ready-made ResearchResponse object.
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        response_format=ResearchResponse,
    )

    # In LangChain 1.x you talk to an agent using a list of "messages".
    # role "user" = the human talking. content = the actual question.
    result = agent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["structured_response"]


# ---------------------------------------------------------------------------
# 7) RUN IT  (trying each model until one works)
# ---------------------------------------------------------------------------
query = input("What can I help you research? ")

structured_response = None
for model_name in MODELS:
    try:
        print(f"[using model: {model_name}]")
        structured_response = run_research(model_name, query)
        break  # success! stop trying other models.
    except Exception as e:
        # "503" / "UNAVAILABLE" means that model is just busy - try the next one.
        if "503" in str(e) or "UNAVAILABLE" in str(e):
            print(f"  {model_name} is busy right now, trying a backup model...")
            continue
        # Any other kind of error is a real problem - show it and stop.
        print("Unexpected error:", e)
        break


# ---------------------------------------------------------------------------
# 8) SHOW THE STRUCTURED ANSWER
# ---------------------------------------------------------------------------
if structured_response is not None:
    print(structured_response)
else:
    print(
        "\nAll models were busy (503). This is temporary on the free tier - "
        "please just run the program again in a minute."
    )
