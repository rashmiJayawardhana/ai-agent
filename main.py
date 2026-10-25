"""
Command line interface for the AI research agent.

Run it with:    python main.py

This file only handles talking to the user: reading questions, printing
answers and exiting cleanly. All the agent logic lives in agent.py.
"""

import sys

from dotenv import load_dotenv

from agent import AgentUnavailableError, ResearchResponse, research


def format_response(response: ResearchResponse) -> str:
    """Turn the structured answer into something pleasant to read in a terminal."""
    lines = [
        "",
        "=" * 70,
        f"TOPIC: {response.topic}",
        "=" * 70,
        "",
        response.summary,
        "",
    ]

    if response.sources:
        lines.append("SOURCES:")
        lines.extend(f"  - {source}" for source in response.sources)
        lines.append("")

    if response.tools_used:
        lines.append(f"TOOLS USED: {', '.join(response.tools_used)}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    # Model output often contains characters (dashes, accents, quotes) that the
    # default Windows console codepage cannot render, which turns them into
    # question marks. Force UTF-8 so answers display correctly everywhere.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass  # Not available on every platform; safe to continue without it.

    # load_dotenv() reads the .env file so GOOGLE_API_KEY is available. Keeping
    # the key in .env rather than in the source means it never reaches git.
    load_dotenv()

    print("AI Research Agent")
    print("Ask a research question, or press Ctrl+C to quit.\n")

    while True:
        try:
            query = input("Research question: ").strip()
        except (KeyboardInterrupt, EOFError):
            # Ctrl+C or a closed stdin should look like a normal exit, not a crash.
            print("\nGoodbye.")
            return 0

        if not query:
            continue

        if query.lower() in {"exit", "quit"}:
            print("Goodbye.")
            return 0

        try:
            # on_status lets the agent report progress (such as falling back to
            # a different model) without agent.py needing to know about printing.
            response = research(query, on_status=lambda message: print(f"  {message}"))
            print(format_response(response))
        except AgentUnavailableError as error:
            # Busy models or exhausted quota: nothing is broken, so report it
            # plainly rather than as a failure.
            print(f"\n{error}\n")
        except KeyboardInterrupt:
            print("\nCancelled.\n")
        except Exception as error:
            # Show the problem but keep the session alive so one bad question
            # does not end the whole program.
            print(f"\nSomething went wrong: {error}\n")


# This guard means the code above runs when you execute `python main.py`, but
# not when another file imports this module.
if __name__ == "__main__":
    sys.exit(main())
