# BYU Speeches - Semantic Search

This is a tool to perform semantic search on the catalog of [BYU Speeches](https://speeches.byu.edu). It scrapes speech transcripts, indexes them using [ColBERT](https://github.com/lightonai/next-plaid) for semantic retrieval, and provides both a CLI and web interface for searching.

Due to copyright, you must run this on your own machine and download the speeches yourself using the included scraper.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (for dependency management)
- [Docker](https://www.docker.com/) and Docker Compose
- A [Hugging Face](https://huggingface.co/) account and access token (optional)

## Setup

### 1. Start services

The project uses Docker Compose to run PostgreSQL (for storing speeches) and NextPlaid (the ColBERT-based search engine).

```bash
export HF_TOKEN=<your-huggingface-token>
docker compose up -d
```

This starts:
- **PostgreSQL** on port `5432` — stores speakers, talks, and paragraph content
- **NextPlaid** on port `8080` — handles semantic indexing and search using the `lightonai/GTE-ModernColBERT-v1` model

### 2. Install dependencies

```bash
uv sync
```

## Usage

All commands are run through the `speeches-search` CLI entry point.

### Scrape speeches

Download all speaker pages and their speech transcripts from speeches.byu.edu into the database:

```bash
uv run speeches-search --scrape
```

This creates the database tables (if they don't already exist), scrapes every speaker and their talks, and stores the text content paragraph-by-paragraph. Already-downloaded talks are skipped on subsequent runs.

### Index speeches

Build the semantic search index from the scraped data:

```bash
uv run speeches-search --index
```

This reads all speakers and talks from the database and indexes each paragraph into NextPlaid. Already-indexed paragraphs are skipped automatically.

### Search speeches (CLI)

Run an interactive search in the terminal:

```bash
uv run speeches-search --search
```

You will be prompted to enter a query and optionally filter by speaker name. Results show matching talks with relevance scores and URLs.

### Search speeches (Web UI)

Start the Flask web interface:

```bash
uv run speeches-search --webapp
```

Then open <http://localhost:8081> in your browser. The web UI supports:
- Free-text semantic search
- Filtering by speaker
- Configurable number of results
- Inline paragraph previews with context

### Reset everything

Drop all database tables and delete the search index:

```bash
uv run speeches-search --drop
```

## Project Structure

```
src/speeches_search/
├── __init__.py          # CLI entry point and argument parsing
├── database.py          # PostgreSQL operations (tables, CRUD)
├── indexer.py           # NextPlaid index management
├── searcher.py          # Search query execution
├── webapp.py            # Flask web application
├── resources.py         # TypedDict definitions (Speaker, Speech)
├── logging.py           # Logger configuration
├── speeches_scrape/
│   └── scrape.py        # Web scraper for speeches.byu.edu
└── templates/
    └── index.html       # Web UI template
```
