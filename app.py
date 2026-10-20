import os
import re
import time
import streamlit as st

from agents import (
    build_reader_agent,
    run_search,
    writer_chain,
    critic_chain,
    invoke_with_retry,
)

from agents import (
    build_reader_agent,
    run_search,
    writer_chain,
    critic_chain,
    invoke_with_retry,
)

# --------------------------------------------------
# Page configuration
# --------------------------------------------------
st.set_page_config(
    page_title="ResearchMind",
    page_icon="R",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MAX_SEARCH_CHARS = 6000
MAX_READER_CHARS = 6000
MAX_RESEARCH_CHARS = 9000

# --------------------------------------------------
# Minimalist styling
# --------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

    :root {
        --bg: #0c0d0f;
        --panel: #121417;
        --panel-soft: #171a1e;
        --border: #292d33;
        --text: #eceef1;
        --muted: #9299a3;
        --accent: #e8a15b;
        --green: #80c99b;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        color: var(--text);
    }
    .stApp { background: var(--bg); }
    #MainMenu, footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1120px; padding: 2rem 2rem 4rem; }

    .brand-row { display:flex; align-items:center; gap:12px; margin-bottom:2.2rem; }
    .brand-mark {
        width:36px; height:36px; display:flex; align-items:center; justify-content:center;
        border:1px solid #45403a; border-radius:10px; color:var(--accent);
        font-family:'IBM Plex Mono', monospace; font-size:15px; font-weight:500;
    }
    .brand-name { font-size:1.05rem; font-weight:700; letter-spacing:-.03em; color:var(--text); }
    .brand-caption { color:var(--muted); font-size:.78rem; margin-top:2px; }

    .hero-title { font-size:clamp(2rem, 4vw, 3.2rem); font-weight:700; letter-spacing:-.055em; line-height:1.08; margin:0; }
    .hero-subtitle { color:var(--muted); font-size:1rem; line-height:1.7; max-width:650px; margin:.9rem 0 1.8rem; }
    .eyebrow { color:var(--accent); text-transform:uppercase; font-family:'IBM Plex Mono',monospace; font-size:.7rem; letter-spacing:.14em; margin-bottom:.8rem; }

    .input-shell { background:var(--panel); border:1px solid var(--border); border-radius:14px; padding:1.25rem 1.3rem .8rem; }
    .stTextInput label { color:#c7cbd1 !important; font-size:.82rem !important; font-weight:600 !important; }
    .stTextInput input { background:#0d0f12 !important; border:1px solid #30353c !important; border-radius:9px !important; color:var(--text) !important; min-height:46px; }
    .stTextInput input:focus { border-color:var(--accent) !important; box-shadow:0 0 0 1px var(--accent) !important; }
    .stButton button, .stDownloadButton button {
        border-radius:9px; border:1px solid #d9954f; background:var(--accent); color:#17130f;
        font-weight:700; min-height:44px; transition:all .15s ease;
    }
    .stButton button:hover, .stDownloadButton button:hover { background:#f0b474; border-color:#f0b474; color:#17130f; }

    .section-title { font-size:1.08rem; font-weight:700; letter-spacing:-.025em; margin:1.8rem 0 .8rem; }
    .section-note { color:var(--muted); font-size:.83rem; margin-top:-.45rem; margin-bottom:1rem; }
    .pipeline-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:1.2rem 0 1.8rem; }
    .pipeline-step { background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:13px 14px; }
    .pipeline-step .num { font-family:'IBM Plex Mono',monospace; font-size:.68rem; color:var(--muted); margin-bottom:9px; }
    .pipeline-step .label { font-size:.84rem; font-weight:600; }
    .pipeline-step .desc { font-size:.72rem; color:var(--muted); margin-top:5px; line-height:1.4; }
    .pipeline-step.active { border-color:#a87542; background:#191713; }
    .pipeline-step.active .num { color:var(--accent); }
    .pipeline-step.done { border-color:#345644; }
    .pipeline-step.done .num { color:var(--green); }

    .report-shell { background:var(--panel); border:1px solid var(--border); border-radius:13px; padding:1.5rem 1.6rem; }
    .report-kicker { color:var(--muted); font-family:'IBM Plex Mono',monospace; font-size:.68rem; letter-spacing:.12em; text-transform:uppercase; margin-bottom:.7rem; }
    .source-item { padding:11px 0; border-bottom:1px solid var(--border); }
    .source-item:last-child { border-bottom:0; }
    .source-index { display:inline-block; min-width:27px; color:var(--muted); font-family:'IBM Plex Mono',monospace; font-size:.75rem; }
    .source-link { color:#e6b27c !important; text-decoration:none; overflow-wrap:anywhere; }
    .source-link:hover { text-decoration:underline; }
    .muted { color:var(--muted); }
    .stExpander { border:1px solid var(--border) !important; border-radius:10px !important; background:var(--panel) !important; }
    [data-testid="stMetric"] { background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:14px; }
    .footer-note { color:#69717b; font-size:.75rem; border-top:1px solid var(--border); padding-top:1rem; margin-top:3rem; }

    @media (max-width: 760px) {
        .block-container { padding:1.25rem 1rem 3rem; }
        .pipeline-grid { grid-template-columns:repeat(2,1fr); }
        .report-shell { padding:1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def extract_sources(text):
    """Extract unique HTTP(S) URLs from source/search text."""
    if not isinstance(text, str):
        return []
    urls = re.findall(r"https?://[^\s<>\"'\])},]+", text)
    found = []
    seen = set()
    for url in urls:
        url = url.rstrip(".,;:")
        if url not in seen:
            seen.add(url)
            found.append(url)
    return found


def last_message_text(result):
    """Extract readable text from a LangChain agent response."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        messages = result.get("messages", [])
        if messages:
            content = getattr(messages[-1], "content", None)
            if content is not None:
                return str(content)
        if result.get("content") is not None:
            return str(result["content"])
    content = getattr(result, "content", None)
    return str(content if content is not None else result)


def render_pipeline(active_step=None, completed_steps=None):
    completed_steps = completed_steps or []
    steps = [
        ("01", "Search", "Find relevant sources"),
        ("02", "Read", "Extract page evidence"),
        ("03", "Write", "Build the report"),
        ("04", "Review", "Check quality"),
    ]
    cards = []
    for num, label, desc in steps:
        status = "done" if label.lower() in completed_steps else "active" if label.lower() == active_step else ""
        cards.append(
            f'<div class="pipeline-step {status}">'
            f'<div class="num">{num}</div>'
            f'<div class="label">{label}</div>'
            f'<div class="desc">{desc}</div>'
            f'</div>'
        )
    st.markdown('<div class="pipeline-grid">' + "".join(cards) + '</div>', unsafe_allow_html=True)


# --------------------------------------------------
# Header
# --------------------------------------------------
st.markdown(
    """
    <div class="brand-row">
      <div class="brand-mark">R.</div>
      <div><div class="brand-name">Research Bot</div><div class="brand-caption">AI research workspace</div></div>
    </div>
    <div class="eyebrow">Multi-agent research</div>
    <h1 class="hero-title">Research, with more signal<br>and less noise.</h1>
    <p class="hero-subtitle">Turn a topic into a structured report. Research Bot searches the web, reads relevant pages, drafts findings, and reviews the result.</p>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# Topic input
# --------------------------------------------------
with st.container(border=False):
    st.markdown('<div class="input-shell">', unsafe_allow_html=True)
    topic = st.text_input(
        "Research topic",
        placeholder="e.g. Recent advances in solid-state batteries",
        key="topic_input",
        label_visibility="visible",
    )
    col_button, col_hint = st.columns([1, 2.7], vertical_alignment="center")
    with col_button:
        run_clicked = st.button("Run research", use_container_width=True)
    with col_hint:
        st.caption("Search · Read · Write · Review")
    st.markdown('</div>', unsafe_allow_html=True)

# Initialize session state.
if "research_result" not in st.session_state:
    st.session_state.research_result = None

# --------------------------------------------------
# Execute pipeline
# --------------------------------------------------
if run_clicked:
    if not topic.strip():
        st.warning("Enter a research topic to get started.")
    else:
        results = {"topic": topic.strip()}
        status_area = st.container()
        with status_area:
            st.markdown('<div class="section-title">Research progress</div>', unsafe_allow_html=True)
            progress_placeholder = st.empty()
            progress_bar = st.progress(0)
            status_text = st.empty()

        try:
            # Step 1: Search
            progress_placeholder.empty()
            render_pipeline(active_step="search")
            status_text.caption("Searching for relevant sources…")
            search_output = run_search(
                f"Find recent, reliable, relevant information about: {topic.strip()}. "
                "Prioritize official sources, reputable news organizations, and primary research. "
                "Return source titles, complete URLs, and useful snippets."
            )
            results["search"] = str(search_output)[:MAX_SEARCH_CHARS]
            results["sources"] = extract_sources(results["search"])
            progress_bar.progress(25)

            # Step 2: Read
            render_pipeline(active_step="read", completed_steps=["search"])
            status_text.caption("Reading a relevant source…")
            if results["sources"]:
                reader_agent = build_reader_agent()
                reader_prompt = f"""Read the most relevant webpage for this topic.

Topic: {topic.strip()}

Search results:
{results['search'][:MAX_SEARCH_CHARS]}

Instructions:
1. Choose a URL exactly as written in the search results.
2. Call web_open with the complete URL in its required url argument.
3. Include the exact source URL in your final response.
4. Extract useful evidence, dates, names, and relevant context.
5. Do not invent facts or URLs.
"""
                reader_result = invoke_with_retry(
                    reader_agent,
                    {"messages": [("user", reader_prompt)]},
                )
                results["reader"] = last_message_text(reader_result)[:MAX_READER_CHARS]
            else:
                results["reader"] = "No URLs were detected in the search output, so webpage reading was skipped."
            results["sources"] = extract_sources(results["search"] + "\n" + results["reader"])
            progress_bar.progress(50)

            # Step 3: Write
            render_pipeline(active_step="write", completed_steps=["search", "read"])
            status_text.caption("Writing the research report…")
            research_material = (
                "SEARCH RESULTS:\n" + results["search"][:3500]
                + "\n\nREAD WEBPAGE CONTENT:\n" + results["reader"][:MAX_READER_CHARS]
                + "\n\nSOURCE URLS:\n" + "\n".join(results["sources"])
            )[:MAX_RESEARCH_CHARS]
            writer_result = invoke_with_retry(
                writer_chain,
                {"topic": topic.strip(), "research": research_material},
            )
            results["writer"] = str(writer_result)

            # Always preserve source links separately. Add a Sources section if absent.
            if results["sources"] and not re.search(r"https?://", results["writer"]):
                results["writer"] += "\n\n## Sources\n" + "\n".join(
                    f"- [{url}]({url})" for url in results["sources"]
                )
            progress_bar.progress(75)

            # Step 4: Critic
            render_pipeline(active_step="review", completed_steps=["search", "read", "write"])
            status_text.caption("Reviewing evidence and report quality…")
            critic_result = invoke_with_retry(
                critic_chain,
                {"report": results["writer"][:6000]},
            )
            results["critic"] = str(critic_result)
            progress_bar.progress(100)
            render_pipeline(completed_steps=["search", "read", "write", "review"])
            status_text.success("Research complete")

        except Exception as exc:
            results["error"] = str(exc)
            st.error(f"The research pipeline stopped: {exc}")
        finally:
            st.session_state.research_result = results

# --------------------------------------------------
# Results
# --------------------------------------------------
r = st.session_state.research_result
if r:
    st.markdown('<div class="section-title">Research results</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-note">Topic: {r.get("topic", "")}</div>', unsafe_allow_html=True)

    if "error" in r:
        with st.expander("Error details", expanded=True):
            st.code(r["error"])

    if "writer" in r:
        st.markdown('<div class="report-shell"><div class="report-kicker">Final report</div>', unsafe_allow_html=True)
        st.markdown(r["writer"])
        st.markdown('</div>', unsafe_allow_html=True)
        st.download_button(
            "Download report (.md)",
            data=r["writer"],
            file_name=f"research_report_{int(time.time())}.md",
            mime="text/markdown",
        )

    source_urls = r.get("sources") or extract_sources(
        str(r.get("search", "")) + "\n" + str(r.get("reader", ""))
    )
    st.markdown('<div class="section-title">Sources</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-note">Links found in the search and reading results.</div>', unsafe_allow_html=True)
    if source_urls:
        for index, url in enumerate(source_urls, start=1):
            st.markdown(
                f'<div class="source-item"><span class="source-index">{index:02d}</span>'
                f'<a class="source-link" href="{url}" target="_blank" rel="noopener noreferrer">{url}</a></div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No source URLs were detected. Expand the raw search output below to inspect the search response.")

    if "critic" in r:
        with st.expander("Review and quality feedback", expanded=False):
            st.markdown(r["critic"])

    with st.expander("Raw search results", expanded=False):
        st.text(r.get("search", "No search output."))
    with st.expander("Extracted webpage content", expanded=False):
        st.text(r.get("reader", "No webpage content."))

st.markdown('<div class="footer-note">ResearchMind · AI-assisted research. Verify important claims against the original sources.</div>', unsafe_allow_html=True)
