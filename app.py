"""
Web interface for the AI research agent, built with Streamlit.

Run it locally with:    streamlit run app.py

Like main.py, this file only handles presentation. The agent itself lives in
agent.py, so the command line app and this web app cannot drift apart.

A note on styling: Streamlit's light/dark setting is chosen by the visitor and
is independent of their operating system preference, so CSS media queries such
as prefers-color-scheme cannot be relied on to detect it. Every custom style
below is therefore built from translucent neutral greys and inherited text
colours, which resolve correctly against either background without the app
needing to know which theme is active.
"""

import html
import os

import streamlit as st
from dotenv import load_dotenv

from agent import AllModelsBusyError, QuotaExceededError, research

load_dotenv()

st.set_page_config(
    page_title="AI Research Agent",
    page_icon="\N{LEFT-POINTING MAGNIFYING GLASS}",
    layout="centered",
)


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

      /* Applied to containers rather than universally, so Streamlit's own
         icon fonts are left alone. */
      .stApp, section[data-testid="stSidebar"] {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      }

      /* Reclaim the generous default headroom above the title. */
      .block-container { padding-top: 3rem; max-width: 46rem; }

      .hero-title {
          font-size: 2.1rem;
          font-weight: 700;
          letter-spacing: -0.021em;
          line-height: 1.15;
          margin: 0 0 0.45rem 0;
      }

      /* Opacity rather than a fixed grey, so secondary text stays correctly
         muted against a white or a near-black background. */
      .hero-subtitle {
          font-size: 1.02rem;
          font-weight: 400;
          line-height: 1.55;
          opacity: 0.72;
          margin: 0 0 0.35rem 0;
      }

      .section-label {
          font-size: 0.74rem;
          font-weight: 600;
          letter-spacing: 0.07em;
          text-transform: uppercase;
          opacity: 0.55;
          margin: 0 0 0.6rem 0;
      }

      /* Translucent grey reads as a subtle tint on light backgrounds and as a
         subtle lift on dark ones, from a single declaration. */
      .pill {
          display: inline-block;
          padding: 0.26rem 0.72rem;
          margin: 0 0.4rem 0.4rem 0;
          border-radius: 999px;
          font-size: 0.8rem;
          font-weight: 500;
          color: inherit;
          background: rgba(128, 128, 128, 0.13);
          border: 1px solid rgba(128, 128, 128, 0.25);
      }

      .answer-body {
          font-size: 1.03rem;
          line-height: 1.68;
          margin: 0.2rem 0 0.4rem 0;
      }

      .source-row {
          font-size: 0.92rem;
          line-height: 1.5;
          padding: 0.42rem 0;
          border-bottom: 1px solid rgba(128, 128, 128, 0.16);
      }
      .source-row:last-child { border-bottom: none; }
      .source-index { opacity: 0.45; margin-right: 0.5rem; font-variant-numeric: tabular-nums; }

      .sidebar-heading {
          font-size: 0.74rem;
          font-weight: 600;
          letter-spacing: 0.07em;
          text-transform: uppercase;
          opacity: 0.55;
          margin: 1.4rem 0 0.5rem 0;
      }
      .sidebar-body { font-size: 0.88rem; line-height: 1.6; opacity: 0.85; }
      .sidebar-item { font-size: 0.88rem; line-height: 1.65; }
      .sidebar-item strong { font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)


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


def format_source(source: str) -> str:
    """Render a source as a tidy link when it is a URL, or as plain text.

    Models return sources in mixed forms: sometimes a bare URL, sometimes a
    label such as "Wikipedia". Full URLs are shortened because an untruncated
    one wraps awkwardly and reads as clutter.

    Everything is escaped: the layout below renders through unsafe_allow_html,
    and model output is influenced by whatever a visitor types, so it must be
    treated as untrusted text rather than as markup.
    """
    text = source.strip()

    if text.startswith(("http://", "https://")):
        label = text.split("//", 1)[1].rstrip("/")
        if len(label) > 58:
            label = label[:55] + "..."
        safe_href = html.escape(text, quote=True)
        return (
            f'<a href="{safe_href}" target="_blank" rel="noopener noreferrer">'
            f"{html.escape(label)}</a>"
        )

    return html.escape(text)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="sidebar-heading" style="margin-top:0">Overview</div>'
        '<div class="sidebar-body">An autonomous research assistant. Given a '
        'question, it selects its own information sources, gathers what it '
        'needs, and returns a structured summary with citations.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-heading">Capabilities</div>'
        '<div class="sidebar-item">'
        '<strong>Web search</strong><br>Current events and recent information'
        '</div>'
        '<div class="sidebar-item" style="margin-top:0.5rem">'
        '<strong>Encyclopaedic lookup</strong><br>Established facts, people and places'
        '</div>'
        '<div class="sidebar-item" style="margin-top:0.5rem">'
        '<strong>Structured reporting</strong><br>Schema-validated output, not free text'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-heading">Method</div>'
        '<div class="sidebar-body">'
        'The agent is given a set of tools and decides which to use at runtime. '
        'No rule in the code maps a question to a source. It may consult '
        'several, review what it finds, and continue until it can answer.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-heading">Reliability</div>'
        '<div class="sidebar-body">'
        'Requests fail over automatically across several models, so a single '
        'overloaded service does not interrupt a session.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-heading">Built with</div>'
        '<div class="sidebar-body">'
        'Google Gemini &middot; LangChain &middot; Pydantic &middot; Streamlit'
        '</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="hero-title">AI Research Agent</div>'
    '<div class="hero-subtitle">Ask a question. The agent chooses its own '
    'sources, gathers the evidence, and returns a concise summary with '
    'citations.</div>',
    unsafe_allow_html=True,
)

st.write("")

# ---------------------------------------------------------------------------
# Query input
# ---------------------------------------------------------------------------
# Most visitors will click an example rather than compose their own question,
# so the demo has to be usable in a single click.
EXAMPLES = [
    "What is retrieval augmented generation?",
    "What causes coral bleaching?",
    "Who was Alan Turing?",
]

st.markdown('<div class="section-label">Start with an example</div>', unsafe_allow_html=True)

for column, example in zip(st.columns(len(EXAMPLES)), EXAMPLES):
    if column.button(example, use_container_width=True):
        st.session_state["query"] = example

query = st.text_input(
    "Your question",
    key="query",
    placeholder="Ask anything, or pick an example above",
    label_visibility="collapsed",
)

submitted = st.button("Research", type="primary", use_container_width=True)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if submitted:
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

            st.divider()

            st.markdown(
                f'<div class="section-label">Topic</div>'
                f'<div class="hero-title" style="font-size:1.45rem;margin-bottom:1.1rem">'
                f"{html.escape(response.topic)}</div>",
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<div class="answer-body">{html.escape(response.summary)}</div>',
                unsafe_allow_html=True,
            )

            if response.sources:
                st.write("")
                rows = "".join(
                    f'<div class="source-row">'
                    f'<span class="source-index">{index}</span>{format_source(source)}'
                    f"</div>"
                    for index, source in enumerate(response.sources, start=1)
                )
                st.markdown(
                    f'<div class="section-label">Sources</div>{rows}',
                    unsafe_allow_html=True,
                )

            if response.tools_used:
                st.write("")
                pills = "".join(
                    f'<span class="pill">{html.escape(tool.replace("_", " "))}</span>'
                    for tool in response.tools_used
                )
                st.markdown(
                    f'<div class="section-label">Sources consulted by the agent</div>{pills}',
                    unsafe_allow_html=True,
                )

        except QuotaExceededError:
            status.empty()
            st.info(
                "**This demo has reached its daily limit.** It runs on a free "
                "allowance that resets every 24 hours, so please try again "
                "tomorrow."
            )
        except AllModelsBusyError:
            status.empty()
            st.info(
                "**The service is busy right now.** This usually clears within "
                "a minute. Please try again."
            )
        except Exception as error:
            status.empty()
            # Visitors get a plain sentence; the technical detail is tucked away
            # so it is still available for debugging without alarming anyone.
            st.error("Something went wrong while researching. Please try again.")
            with st.expander("Technical details"):
                st.code(f"{type(error).__name__}: {error}")
