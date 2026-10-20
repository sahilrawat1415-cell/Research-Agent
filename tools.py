import os
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain.tools import tool
from tavily import TavilyClient

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise EnvironmentError("TAVILY_API_KEY is missing. Add it to your .env file.")

tavily = TavilyClient(api_key=TAVILY_API_KEY)


def _is_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


@tool
def web_search(query: str) -> str:
    """Search the web using Tavily and return page titles, full URLs, and snippets."""
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")

    response = tavily.search(query=query.strip(), max_results=5)
    results = response.get("results", [])

    if not results:
        return "No search results were returned by Tavily."

    output = []
    for index, item in enumerate(results, start=1):
        title = item.get("title") or "Untitled source"
        url = item.get("url") or ""
        snippet = item.get("content") or item.get("snippet") or ""
        output.append(
            f"Source {index}: {title}\n"
            f"URL: {url}\n"
            f"Snippet: {snippet[:500]}"
        )

    return "\n\n---\n\n".join(output)


@tool
def web_open(url: str) -> str:
    """Open a complete HTTP or HTTPS webpage URL and return its source URL and clean text."""
    if not _is_http_url(url):
        return f"Invalid webpage URL: {url!r}. Provide a complete http:// or https:// URL."

    try:
        response = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ResearchMind/1.0)"},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        title = soup.title.get_text(" ", strip=True) if soup.title else "Untitled webpage"
        text = soup.get_text(separator=" ", strip=True)
        text = " ".join(text.split())[:6000]

        return (
            f"SOURCE TITLE: {title}\n"
            f"SOURCE URL: {url}\n\n"
            f"WEBPAGE CONTENT:\n{text}"
        )
    except requests.RequestException as exc:
        return f"SOURCE URL: {url}\nCould not open webpage: {exc}"
    except Exception as exc:
        return f"SOURCE URL: {url}\nUnexpected webpage-reading error: {exc}"
