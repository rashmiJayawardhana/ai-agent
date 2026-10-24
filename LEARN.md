# Understanding This Project (Beginner Guide)

This is an **AI research agent**. You ask a question, and an AI (Google Gemini)
answers it — but it can also *use tools* (web search, Wikipedia, save-to-file)
to help itself. Then it returns a neat, structured answer.

---

## The big idea: what is an "AI agent"?

A plain AI model only reads text and writes text back. It can't search the web
or save files on its own.

An **agent** is an AI model that has been given **tools** and the ability to
**decide when to use them**. The loop looks like this:

```
You ask a question
      │
      ▼
  AI thinks  ──►  "I need to search the web"  ──►  runs the search tool
      ▲                                                     │
      └───────────────  reads the result  ◄────────────────┘
      │
      ▼
  AI has enough info  ──►  writes the final structured answer
```

---

## The files

| File               | What it does |
|--------------------|--------------|
| `main.py`          | The main program — builds the AI, the prompt, and the agent, then runs it. |
| `tools.py`         | Defines the 3 tools the AI can use (search, Wikipedia, save-to-file). |
| `.env`             | Stores your secret API key. **Never share or commit this.** |
| `requirements.txt` | The list of libraries this project needs. |
| `.gitignore`       | Tells Git which files to NOT upload (keeps `.env` secret). |

---

## Key concepts (the words you'll keep seeing)

- **LLM** = Large Language Model (the "brain", here Gemini). It predicts text.
- **LangChain** = a library that gives every AI provider the same simple interface,
  and provides the agent/tool machinery.
- **Prompt** = the instructions you send the AI. A *prompt template* is a reusable
  prompt with blanks (like `{query}`) you fill in.
- **Tool** = a function the AI is allowed to call (search, save, etc.).
- **Agent** = an LLM + tools + the logic to choose tools.
- **AgentExecutor** = the engine that actually runs the think→tool→think loop.
- **Pydantic / BaseModel** = a way to define the exact *shape* of data you want
  (here: topic, summary, sources, tools_used) so your code can rely on it.
- **Parser** = turns the AI's text reply into that structured shape.
- **`.env` + `load_dotenv()`** = keeps secrets out of your code; loads them at runtime.

---

## How to run it

1. Make sure your virtual environment is active (you'll see `(venv)` in the terminal).
2. Install the libraries (only needed once):
   ```powershell
   pip install -r requirements.txt
   ```
3. Put your Google API key in `.env`:
   ```
   GOOGLE_API_KEY="your-key-here"
   ```
   Get one free at https://aistudio.google.com/apikey
4. Run it:
   ```powershell
   python .\main.py
   ```
5. Type a question when prompted, e.g. *"the history of coffee"*.

You'll see the agent "think" in the terminal (because `verbose=True`), and if it
chooses the save tool, results land in `research_output.txt`.

---

## Common errors and what they mean

- **"Could not resolve authentication method" / "no API key"**
  → Your API key is missing or empty in `.env`.

- **`404 ... model ... is no longer available`**
  → The model name in `main.py` is outdated. Update the name in this line:
  ```python
  llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", max_retries=2)
  ```

- **`503 ... high demand` / "All models were busy"**
  → Not a bug in your code — the model's server is temporarily overloaded
  (common on the free tier). `main.py` already handles this: it lists several
  models in `MODELS` and automatically falls back to the next one if the first
  is busy. If you see "All models were busy", every model was overloaded at
  once — just run the program again in a minute, or add more model names to the
  `MODELS` list.

- **`ImportError: cannot import name 'create_tool_calling_agent'` (or `'Tool'`)**
  → You're on LangChain 1.x, where the API changed. This project is already
  updated for it: it uses `create_agent` (not `create_tool_calling_agent`)
  and imports `tool`/`Tool` from `langchain_core.tools`.

- **`Could not import ddgs ... pip install -U ddgs`**
  → The web-search package was renamed. Run `pip install -U ddgs`.
  To see which model names your key can use:
  ```python
  import os
  from dotenv import load_dotenv
  from google import genai
  load_dotenv()
  client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
  for m in client.models.list():
      print(m.name, m.supported_actions)
  ```

- **"Error parsing response"**
  → The AI didn't reply in the exact format we asked for. The code prints the raw
  reply so you can see what it actually said. Usually re-running fixes it.

---

## Things to try next (to learn by tinkering)

- Change the `doc_content_chars_max=100` in `tools.py` to `1000` for richer Wikipedia text.
- Edit the `"system"` message in `main.py` to change the AI's personality or rules.
- Add a new field to `ResearchResponse` (e.g. `key_people: list[str]`) and watch the
  AI start filling it in.
