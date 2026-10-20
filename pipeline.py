import re

from agents import (
    build_reader_agent,
    run_search,
    writer_chain,
    critic_chain,
    invoke_with_retry,
)

MAX_SEARCH_CHARS = 6000
MAX_READER_SEARCH_CHARS = 4000
MAX_SCRAPED_CHARS = 6000
MAX_RESEARCH_CHARS = 9000
MAX_CRITIC_CHARS = 6000


def extract_sources(text: str) -> list[dict]:
    """Extract unique HTTP(S) URLs and nearby titles from research text."""
    if not isinstance(text, str):
        return []

    sources = []
    seen = set()
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.search(r"https?://[^\s<>\"'\])},]+", line)
        if not match:
            continue
        url = match.group(0).rstrip(".,;:")
        if url in seen:
            continue
        seen.add(url)
        title = "Source"
        for prior in reversed(lines[max(0, index - 2):index + 1]):
            title_match = re.search(r"(?:Title|Source title)\s*:\s*(.+)", prior, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                break
        sources.append({"title": title, "url": url})
    return sources


def get_last_message_text(result) -> str:
    """Safely get text from common LangChain agent result structures."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        messages = result.get("messages", [])
        if messages:
            content = getattr(messages[-1], "content", None)
            if content is not None:
                return str(content)
        content = result.get("content")
        if content is not None:
            return str(content)
    content = getattr(result, "content", None)
    return str(content if content is not None else result)


def run_research_pipeline(topic: str) -> dict:
    state = {
        "topic": topic,
        "search_results": "",
        "scraped_content": "",
        "sources": [],
        "report": "",
        "feedback": "",
    }

    if not topic or not topic.strip():
        raise ValueError("Research topic cannot be empty.")
    topic = topic.strip()
    state["topic"] = topic

    # STEP 1: SEARCH
    print("\n" + "=" * 50)
    print("STEP 1 - SEARCHING THE WEB")
    print("=" * 50)
    try:
        search_result = run_search(
            f"Find recent, reliable and detailed information about: {topic}"
        )
        state["search_results"] = str(search_result)[:MAX_SEARCH_CHARS]
        state["sources"] = extract_sources(state["search_results"])
        print(state["search_results"])
    except Exception as exc:
        state["error"] = f"Search failed: {exc}"
        print(state["error"])
        return state

    # STEP 2: READER
    print("\n" + "=" * 50)
    print("STEP 2 - READER AGENT")
    print("=" * 50)
    try:
        reader_agent = build_reader_agent()
        reader_prompt = f"""Read the most relevant webpage for this topic.

Topic: {topic}

Search results (use a URL exactly as supplied here):
{state['search_results'][:MAX_READER_SEARCH_CHARS]}

Instructions:
1. Select a relevant URL from the search results.
2. Call web_open with the complete URL in its required `url` argument.
3. Extract useful information and preserve the exact source URL and title.
4. Do not invent URLs or facts.
5. If no URL is available, say so.
"""
        reader_result = invoke_with_retry(
            reader_agent, {"messages": [("user", reader_prompt)]}
        )
        state["scraped_content"] = get_last_message_text(reader_result)[:MAX_SCRAPED_CHARS]
        state["sources"] = extract_sources(
            state["search_results"] + "\n" + state["scraped_content"]
        )
        print(state["scraped_content"])
    except Exception as exc:
        print(f"Reader failed: {exc}")
        state["scraped_content"] = (
            "Webpage reading failed; use the search results below.\n\n"
            + state["search_results"]
        )

    # STEP 3: WRITER
    print("\n" + "=" * 50)
    print("STEP 3 - WRITER")
    print("=" * 50)
    research_combined = (
        "SEARCH RESULTS:\n" + state["search_results"][:3000]
        + "\n\nDETAILED SCRAPED CONTENT:\n"
        + state["scraped_content"][:MAX_SCRAPED_CHARS]
    )[:MAX_RESEARCH_CHARS]

    try:
        state["report"] = invoke_with_retry(
            writer_chain, {"topic": topic, "research": research_combined}
        )
        state["report"] = str(state["report"])
        # Ensure source URLs appear in the report even if the model omits them.
        report_sources = extract_sources(
            state["search_results"] + "\n" + state["scraped_content"]
        )
        if report_sources:
            source_block = "\n\n## Sources\n" + "\n".join(
                f"- [{source['title']}]({source['url']})"
                for source in report_sources
            )
            if not extract_sources(state["report"]):
                state["report"] += source_block
        print(state["report"])
    except Exception as exc:
        state["error"] = f"Writer failed: {exc}"
        print(state["error"])
        return state

    # STEP 4: CRITIC
    print("\n" + "=" * 50)
    print("STEP 4 - CRITIC")
    print("=" * 50)
    try:
        state["feedback"] = invoke_with_retry(
            critic_chain, {"report": state["report"][:MAX_CRITIC_CHARS]}
        )
        print(state["feedback"])
    except Exception as exc:
        state["feedback"] = f"Critic evaluation failed: {exc}"
        print(state["feedback"])

    print("\n" + "=" * 50)
    print("RESEARCH PIPELINE COMPLETED")
    print("=" * 50)
    return state


if __name__ == "__main__":
    topic = input("\nEnter a research topic: ").strip()
    if topic:
        results = run_research_pipeline(topic)
        print("\n\nPIPELINE OUTPUT")
        print("=" * 50)
        for key, value in results.items():
            print(f"\n{key.upper()}:\n")
            print(value)
    else:
        print("Please enter a valid research topic.")
