# Understanding This Project (Beginner Guide)

This is an **AI research agent**. You ask a question, and an AI (Google Gemini)
answers it, but it can also *use tools* (web search, Wikipedia, save-to-file)
to help itself. Then it returns a neat, structured answer.

---

## The big idea: what is an "AI agent"?

A plain AI model only reads text and writes text back. It can't search the web
or save files on its own.

An **agent** is an AI model that has been given **tools** and the ability to
**decide when to use them**. The loop looks like this:

```
You ask a question
      |
      v
  AI thinks  -->  "I need to search the web"  -->  runs the search tool
      ^                                                  |
      +---------------  reads the result  <--------------+
      |
      v
  AI has enough info  -->  writes the final structured answer
```

The important part is that **nothing in the code decides which tool to use**.
We hand the model a set of tools and a description of each, and it picks.

---

## The files

| File               | What it does |
|--------------------|--------------|
| `agent.py`         | The core. Builds the AI, its prompt and tools, and exposes one `research()` function. |
| `tools.py`         | Defines the 3 tools the AI can use (search, Wikipedia, save-to-file). |
| `main.py`          | The command line interface. Asks you questions and prints answers. |
| `app.py`           | The web interface (Streamlit), same agent in a browser. |
| `.env`             | Stores your secret API key. **Never share or commit this.** |
| `.env.example`     | A safe template showing which keys are needed. |
| `requirements.txt` | The list of libraries this project needs, with exact versions. |
| `.gitignore`       | Tells Git which files to NOT upload (keeps `.env` secret). |

**Why is the agent in its own file?** Because two different interfaces (`main.py`
and `app.py`) both need it. If the agent logic lived inside `main.py`, the web
app would need its own copy, and the two would slowly drift apart as you change
one and forget the other.

---

## Key concepts (the words you'll keep seeing)

- **LLM** = Large Language Model (the "brain", here Gemini). It predicts text.
- **LangChain** = a library that gives every AI provider the same simple
  interface, and provides the agent/tool machinery.
- **Prompt** = the instructions you send the AI. The **system prompt** is the
  standing instruction set that applies to every question.
- **Tool** = a function the AI is allowed to call (search, save, etc.). Its
  description is what the AI reads to decide whether it is relevant.
- **Agent** = an LLM + tools + the ability to choose among them.
- **`create_agent`** = the single LangChain 1.x function that wires all of that
  together. (Older tutorials use `create_tool_calling_agent` and
  `AgentExecutor`; both were removed in LangChain 1.x.)
- **Pydantic / BaseModel** = a way to define the exact *shape* of data you want
  (here: topic, summary, sources, tools_used) so your code can rely on it.
- **`response_format`** = telling `create_agent` to return that shape. The
  answer arrives already built and validated, so there is no text to parse.
- **`.env` + `load_dotenv()`** = keeps secrets out of your code; loads them at
  runtime.

---

## How to run it

1. Make sure your virtual environment is active (you'll see `(venv)` in the terminal).
2. Install the libraries (only needed once):
   ```powershell
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and put your Google API key in it:
   ```
   GOOGLE_API_KEY="your-key-here"
   ```
   Get one free at https://aistudio.google.com/apikey
4. Run whichever interface you prefer:
   ```powershell
   python .\main.py          # terminal
   streamlit run app.py      # browser
   ```
5. Type a question, e.g. *"the history of coffee"*. Type `exit` to quit the
   terminal version.

If the agent chooses the save tool, results land in `research_output.txt`.

---

## Common errors and what they mean

- **"Could not resolve authentication method" / "no API key"**
  Your API key is missing or empty in `.env`.

- **`503 ... high demand` / "Every model is currently overloaded"**
  Not a bug in your code. The model's server is temporarily busy, which is
  common on the free tier. `agent.py` already handles this: it lists several
  models in `MODELS` and automatically falls back to the next one. If every
  model is busy at once, wait a minute and try again, or add more model names
  to the `MODELS` list.

- **`404 ... model is no longer available`**
  Google renamed or retired the model. Update the names in `MODELS` in
  `agent.py`. To see which models your key can actually use:
  ```python
  import os
  from dotenv import load_dotenv
  from google import genai
  load_dotenv()
  client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
  for m in client.models.list():
      print(m.name, m.supported_actions)
  ```

- **`ImportError: cannot import name 'create_tool_calling_agent'` (or `'Tool'`)**
  You're following a LangChain 0.x tutorial on LangChain 1.x. This project is
  already updated: it uses `create_agent`, and imports `tool` from
  `langchain_core.tools`.

- **`Could not import ddgs ... pip install -U ddgs`**
  The web-search package was renamed from `duckduckgo-search`. Run
  `pip install -U ddgs`.

- **`JSONDecodeError` from Wikipedia**
  Wikipedia rate-limited the request (HTTP 429) because the `wikipedia`
  package's default User-Agent is shared by everyone. `tools.py` fixes this by
  setting a specific User-Agent.

- **`Warning: there are non-text parts in the response`**
  Harmless. LangChain is just noting the model sent a tool call alongside text.

---

## Things to try next (to learn by tinkering)

- Change `doc_content_chars_max=100` in `tools.py` to `1000` for richer
  Wikipedia text.
- Edit `SYSTEM_PROMPT` in `agent.py` to change how the agent behaves.
- Add a field to `ResearchResponse` in `agent.py` (e.g.
  `key_people: list[str]`) and watch the AI start filling it in.
- Write your own tool in `tools.py` using the `@tool` decorator, add it to
  `TOOLS` in `agent.py`, and see whether the agent chooses to use it. The
  description you write is what makes the agent pick it.
