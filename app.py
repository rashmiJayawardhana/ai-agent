"""
Web interface for the AI research agent, built with Streamlit.

Run it locally with:    streamlit run app.py

Like main.py, this file only handles presentation. The agent itself lives in
agent.py, so the command line app and this web app cannot drift apart.
"""

import os

import streamlit as st
from dotenv import load_dotenv

from agent import MODELS, AllModelsBusyError, QuotaExceededError, research

load_dotenv()

st.set_page_config(page_title="AI Research Agent", page_icon="\N{LEFT-POINTING MAGNIFYING GLASS}", layout="centered")


def get_api_key() -> str | None:
    """Find the Gemini API key.

    The key is supplied by whoever runs the app, never by the visitor. Most
    people viewing a demo like this have no idea what an API key is, so asking
    for one would read as the page being broken.

    Order of preference:
      1. Streamlit's secrets store, used when this is deployed.
      2. The GOOGLE_API_KEY environment variable, used when running locally.
    """
    # st.secrets raises if no secrets file exists, which is normal when running
    # locally from a .env file, so treat a failure here as simply "not found".
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
    except Exception:
        pass

    return os.environ.get("GOOGLE_API_KEY")


# ---------------------------------------------------------------------------
# Sidebar: what this is and how it works
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("About")
    st.write(
        "An AI agent that researches a question by deciding for itself which "
        "tools to use, then returns a structured, sourced answer."
    )

    st.subheader("Tools available to the agent")
    st.markdown(
        "- **Web search** (DuckDuckGo) for current information\n"
        "- **Wikipedia** for established facts\n"
        "- **File save** for exporting a result"
    )

    st.subheader("Built with")
    st.markdown(
        "- Google Gemini\n"
        "- LangChain 1.x (`create_agent`)\n"
        "- Pydantic for validated output\n"
        "- Streamlit"
    )

    st.caption(f"Model fallback chain: {' -> '.join(MODELS)}")


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------
st.title("AI Research Agent")
st.caption(
    "Ask a question. The agent chooses its own tools, gathers information, "
    "and returns a structured summary with sources."
)

# Example questions matter: most visitors will click one rather than think of
# their own, so the demo needs to be usable with a single click.
EXAMPLES = [
    "What is the capital of Sri Lanka?",
    "What is retrieval augmented generation?",
    "Who was Alan Turing?",
]

st.write("**Try an example:**")
example_columns = st.columns(len(EXAMPLES))
for column, example in zip(example_columns, EXAMPLES):
    if column.button(example, use_container_width=True):
        st.session_state["query"] = example

query = st.text_input(
    "Your research question",
    key="query",
    placeholder="e.g. What are the main causes of coral bleaching?",
)

if st.button("Research", type="primary"):
    api_key = get_api_key()

    if not query.strip():
        st.warning("Please enter a question first.")
    elif not api_key:
        # Only the person running the app can fix this, so the message is
        # addressed to them while staying calm for anyone else who sees it.
        st.error(
            "This demo is not configured yet. Whoever is running it needs to "
            "set a GOOGLE_API_KEY (in .env locally, or in Streamlit secrets "
            "when deployed)."
        )
    else:
        status = st.empty()
        try:
            with st.spinner("Researching..."):
                response = research(
                    query,
                    api_key=api_key,
                    on_status=lambda message: status.caption(message),
                )
            status.empty()

            st.subheader(response.topic)
            st.write(response.summary)

            if response.sources:
                st.markdown("**Sources**")
                for source in response.sources:
                    st.markdown(f"- {source}")

            if response.tools_used:
                st.markdown("**Tools the agent chose to use**")
                st.write(", ".join(response.tools_used))

            with st.expander("Raw structured output"):
                # Showing the validated object makes the structured-output
                # design visible rather than just claimed.
                st.json(response.model_dump())

        except QuotaExceededError:
            status.empty()
            st.info(
                "**This demo has reached its daily limit.** It runs on a free "
                "allowance that resets every 24 hours, so please try again "
                "tomorrow. You can still browse the source code to see how it "
                "works."
            )
        except AllModelsBusyError:
            status.empty()
            st.info(
                "**The AI service is busy right now.** This happens on the "
                "free tier and usually clears within a minute. Please try again."
            )
        except Exception as error:
            status.empty()
            # Visitors get a plain sentence; the technical detail is tucked away
            # so it is still available for debugging without alarming anyone.
            st.error("Something went wrong while researching. Please try again.")
            with st.expander("Technical details"):
                st.code(f"{type(error).__name__}: {error}")
