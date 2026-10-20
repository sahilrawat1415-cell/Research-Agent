import os
import time
import re

from dotenv import load_dotenv
from groq import RateLimitError
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from tools import web_search, web_open

load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    raise EnvironmentError("GROQ_API_KEY is missing. Add it to your .env file.")

# Keep the Groq model used by your project.
llm = ChatGroq(
    model="openai/gpt-oss-120b",
    max_tokens=1024,
    temperature=0,
)


def invoke_with_retry(runnable, inputs, max_retries=3):
    """Retry transient Groq rate-limit errors using the suggested wait time."""
    for attempt in range(max_retries + 1):
        try:
            return runnable.invoke(inputs)
        except RateLimitError as exc:
            if attempt >= max_retries:
                raise
            match = re.search(r"try again in ([\d.]+)s", str(exc), re.IGNORECASE)
            delay = float(match.group(1)) + 1 if match else min(5 * (2 ** attempt), 60)
            print(f"Groq rate limit reached; retrying in {delay:.1f} seconds...")
            time.sleep(delay)


def build_search_agent():
    """Build a search agent for cases where LLM-based tool selection is needed."""
    return create_agent(
        model=llm,
        tools=[web_search],
        system_prompt=(
            "You are a web research search agent. Use web_search with a query. "
            "Return the result titles, exact URLs, and snippets. Never invent URLs. "
            "Do not call tools that are not registered."
        ),
    )


def build_reader_agent():
    """Build a reader agent that opens URLs supplied in the user message."""
    return create_agent(
        model=llm,
        tools=[web_open],
        system_prompt=(
            "You are a webpage-reading agent. Use only URLs present in the supplied search results. "
            "When calling web_open, ALWAYS provide the complete URL in the required `url` argument. "
            "Never call web_open without a valid URL. Do not use web_search. "
            "Summarize the opened page accurately and preserve its exact source title and URL. "
            "If no valid URL is available, say so rather than inventing one."
        ),
    )


writer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are a professional research analyst and fact-checker.

Your job is to produce accurate, evidence-based research reports.

STRICT RULES:

1. SOURCE CREDIBILITY
- Prefer official government documents, primary sources,
  established news organizations, academic papers, and
  reputable research institutions.
- Treat blogs, social media posts, and YouTube videos as
  secondary or unverified sources unless independently verified.
- Never claim that a source is reliable without justification.

2. FACTUAL ACCURACY
- Do not invent facts, dates, statistics, quotations, or URLs.
- Distinguish verified facts from estimates and allegations.
- If sources disagree, explain the disagreement.
- If evidence is insufficient, explicitly acknowledge it.

3. CITATIONS
- Cite factual claims using numbered references: [1], [2], etc.
- Every numbered citation must correspond to an entry in Sources.
- Preserve source URLs exactly as supplied.
- Never fabricate a URL or citation.
- Place citations near the claims they support.

4. NUMERICAL CLAIMS
- Include the date, source, and context for important statistics.
- Explain differences between estimates when relevant.
- Never present estimates as confirmed facts.

5. ANALYSIS
- Explain causes, consequences, and broader implications.
- Include historical comparisons when supported by evidence.
- Separate factual reporting from interpretation.
- Present relevant competing explanations.

6. WRITING QUALITY
- Use complete sentences and clear paragraphs.
- Avoid repetition and unsupported conclusions.
- Proofread the entire report before returning it.
- Do not truncate sections or leave incomplete sentences.

7. TRANSPARENCY
- If the research does not support a conclusion, say so.
- Do not pretend to have verified information that was not checked.
"""
    ),
    (
        "human",
        """
Prepare a detailed research report on this topic:

{topic}

RESEARCH MATERIAL:
{research}

Use this structure:

# 1. Executive Summary
Summarize the most important findings.

# 2. Background
Explain the context and relevant history.

# 3. Key Findings
Present at least three substantial findings.
Support factual claims with numbered citations.

# 4. Evidence and Source Evaluation
Explain which sources support the findings.
Identify conflicting claims and evidence limitations.

# 5. Analysis
Explain causes, consequences, and broader implications.
Include comparisons where the supplied evidence supports them.

# 6. Limitations
Identify missing data, uncertainty, and unresolved questions.

# 7. Conclusion
Summarize what the available evidence establishes.

# 8. Sources
Provide a numbered bibliography matching the in-text citations.

Format each source as:

[1] Page title — https://actual-source-url

Only use URLs present in the research material.

Do not invent references. If a source cannot be verified,
identify that limitation explicitly.
"""
    ),
])

writer_chain = writer_prompt | llm | StrOutputParser()


critic_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a strict, constructive research critic. Evaluate accuracy, evidence, clarity, and source quality."
    ),
    (
        "human",
        """Review the report below.

Report:
{report}


Evaluate the research report using the following criteria:

1. Source credibility: 25%
2. Citation accuracy and traceability: 25%
3. Factual accuracy and evidence: 20%
4. Depth of analysis: 15%
5. Clarity, completeness, and balance: 15%

Return:

Score: X/10

Strengths:
- Identify specific strengths.

Areas to Improve:
- Identify specific weaknesses.
- Explain which claims lack adequate evidence.
- Identify missing or mismatched citations.
- Flag questionable sources and unsupported statistics.
- Identify incomplete sentences or unsupported conclusions.

One line verdict:
Give an honest summary of the report's reliability.

Do not claim to have independently verified sources unless
the supplied evidence demonstrates that verification.
Do not inflate the score merely because the report is lengthy.
""",
    ),
])
critic_chain = critic_prompt | llm | StrOutputParser()


def run_search(query: str) -> str:
    """Run Tavily search directly, avoiding unnecessary LLM tool selection."""
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")
    return web_search.invoke({"query": query.strip()})
