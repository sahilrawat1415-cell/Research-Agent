# Research-Agent
Live Demo: https://research-agent-jddqunjm6vwgovlrhxtxak.streamlit.app/
An AI-assisted, multi-agent research application that turns a topic into
a structured research report. It searches the web, reads a relevant
webpage, drafts an evidence-based report, and asks a critic agent to
review the report's quality.

The project uses **Groq** for language-model inference, **Tavily** for
web search, and **Streamlit** for the web interface.

## Features

-   **Web search:** Retrieves relevant results with titles, URLs, and
    snippets using Tavily.
-   **Webpage reading:** Opens a selected HTTP/HTTPS URL and extracts
    readable page text.
-   **Report generation:** Produces a structured report with an
    executive summary, background, key findings, source evaluation,
    analysis, limitations, conclusion, and sources.
-   **Quality review:** A critic evaluates source credibility, citation
    traceability, factual support, analytical depth, clarity, and
    balance.
-   **Retry handling:** Retries transient Groq rate-limit errors with a
    delay.
-   **Source links:** Displays detected source URLs in the interface.
-   **Markdown export:** Lets users download the generated report as a
    Markdown file.
-   **CLI pipeline:** Also supports running the research workflow from
    the terminal.

## How the workflow works

1.  **Search** --- Tavily searches for information related to the topic.
2.  **Read** --- a reader agent opens a relevant URL returned by search.
3.  **Write** --- the writer model uses the collected research material
    to draft the report.
4.  **Review** --- the critic evaluates the report and returns a score,
    strengths, weaknesses, and a verdict.

The web interface is implemented in `app.py`. The agent/model setup and
prompts are in `agents.py`, web tools are in `tools.py`, and the
terminal-oriented workflow is in `pipeline.py`.

## Tech stack

-   Python
-   Streamlit
-   LangChain
-   Groq (`langchain-groq`)
-   Tavily Search API (`tavily-python`)
-   Requests
-   Beautiful Soup

## Project structure

``` text
Research-Agent/
├── app.py
├── agents.py
├── pipeline.py
├── tools.py
├── requirements.txt
├── .env.example       # Optional template; create this yourself
└── .gitignore
```

Do not commit `.env`, API keys, or your virtual environment.

## Requirements

-   Python 3.10 or newer is recommended.
-   A Groq API key.
-   A Tavily API key.
-   Internet access.

## Installation

### 1. Clone the repository

``` bash
git clone https://github.com/sahilrawat1415-cell/Research-Agent.git
cd Research-Agent
```

### 2. Create and activate a virtual environment

**Windows PowerShell:**

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can run the commands from Command
Prompt instead:

``` bat
.venv\Scripts\activate.bat
```

**macOS/Linux:**

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

``` bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install streamlit
```

`streamlit` is required by the web interface. If it is not listed in
your current `requirements.txt`, add this line to that file so future
installations include it:

``` text
streamlit
```

### 4. Configure environment variables

Create a file named `.env` in the project root:

``` env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
```

Replace the example values with your own keys. Do not share the `.env`
file or push it to GitHub.

The application loads these values through `python-dotenv`. It uses the
Groq model configured in `agents.py` (`openai/gpt-oss-120b`).

## Run the application

### Streamlit web interface

From the project root, run:

``` bash
streamlit run app.py
```

Streamlit will print a local URL in the terminal, usually
`http://localhost:8501`. Open that address in your browser, enter a
research topic, and select **Run research**.

### Command-line pipeline

To run the research pipeline without the Streamlit interface:

``` bash
python pipeline.py
```

Enter a topic when prompted. The pipeline prints the search output,
extracted webpage content, report, and critic feedback in the terminal.

## Generated report structure

The writer prompt asks for these sections:

1.  Executive Summary
2.  Background
3.  Key Findings
4.  Evidence and Source Evaluation
5.  Analysis
6.  Limitations
7.  Conclusion
8.  Sources

The critic returns a score out of 10, strengths, areas to improve, and a
one-line verdict.

## Important limitations

-   **AI output can be wrong.** Verify important claims against the
    original sources.
-   Search results and webpage extraction depend on third-party services
    and website accessibility.
-   Some sites block automated requests or render content with
    JavaScript, so their full content may not be extracted.
-   A source URL appearing in a report does not by itself prove that
    every claim is supported by that source.
-   The critic is an automated review, not an independent guarantee of
    factual accuracy.
-   API usage may be subject to provider rate limits, quotas, and
    pricing.

## Troubleshooting

### Missing API key

If you see an error saying `GROQ_API_KEY` or `TAVILY_API_KEY` is
missing, check that `.env` exists in the project root and contains both
variables with valid values.

### Missing Python package

Activate the project's virtual environment, then install the
dependencies:

``` bash
pip install -r requirements.txt
pip install streamlit
```

### Groq rate limit

The application retries some rate-limit errors automatically. If limits
persist, wait before retrying and check your Groq account's current
limits.

### Webpage could not be opened

The site may block automated requests, require JavaScript, or be
temporarily unavailable. Try another source URL.

## Security

-   Keep API keys in `.env` or a secret manager.
-   Never commit credentials, tokens, or private research data.
-   If an API key is accidentally exposed, revoke or rotate it
    immediately.

## License

No license is specified in this repository yet. Add a `LICENSE` file if
you want to publish explicit terms for reuse.
