# CLAUDE.md — PDF RAG Project

This file gives Claude Code context about this project so it can assist effectively.

---

## Project Overview

A **Claude-native Retrieval-Augmented Generation (RAG)** system that lets you chat with any PDF.
Built as a learning POC for an aspiring AI PM — no LangChain, everything wired from scratch so
each step is visible and understandable.

---

## Tech Stack

| Component         | Tool                              | Notes                                  |
|-------------------|-----------------------------------|----------------------------------------|
| LLM               | Claude (`claude-3-5-haiku`)       | Via Anthropic SDK                      |
| Embeddings        | `sentence-transformers`           | Local model, no API cost               |
| Embedding model   | `all-MiniLM-L6-v2`                | ~80MB, downloads on first run          |
| Vector DB         | ChromaDB (`PersistentClient`)     | Stored locally in `./chroma_db/`       |
| PDF Parser        | `pypdf`                           | Pure Python, no system dependencies    |
| Python            | 3.9+                              | Managed via `venv`                     |

---

## Project Structure

```
pdf-rag/
├── rag.py              # All-in-one app — START HERE
├── ingest.py           # Standalone ingestion pipeline
├── query.py            # Standalone query module
├── requirements.txt    # Python dependencies
├── .gitignore          # Excludes venv/, chroma_db/, *.pdf, .env
├── CLAUDE.md           # This file
├── venv/               # Virtual environment (not committed)
└── chroma_db/          # Vector database on disk (not committed)
```

---

## Key Config Values

All tunable constants live at the top of each file:

| Variable   | Default | Effect                                              |
|------------|---------|-----------------------------------------------------|
| `PDF_PATH` | `"your_doc.pdf"` | Path to the PDF to ingest                |
| `DB_PATH`  | `"./chroma_db"`  | Where ChromaDB persists vectors          |
| `MODEL`    | `"claude-3-5-haiku-20241022"` | Claude model for generation   |
| `TOP_K`    | `4`     | Number of chunks retrieved per question             |
| `CHUNK_SZ` | `500`   | Characters per chunk during ingestion               |
| `OVERLAP`  | `50`    | Character overlap between adjacent chunks           |

---

## Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...   # Required — get from console.anthropic.com
```

Set it permanently:
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

---

## Setup

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set API key
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

---

## Running the App

### Option A — All-in-one (recommended)
```bash
source venv/bin/activate
python3 rag.py
```
- Auto-ingests the PDF if `chroma_db/` doesn't exist
- Drops straight into the Q&A chat loop

### Option B — Separate steps
```bash
# Step 1: Ingest (run once per PDF)
python3 ingest.py

# Step 2: Query (run as many times as you want)
python3 query.py
```

---

## In-app Commands (while chatting in rag.py)

| Command    | What it does                                          |
|------------|-------------------------------------------------------|
| `reingest` | Re-reads and re-embeds the PDF (use after PDF change) |
| `chunks`   | Shows the raw retrieved chunks from the last query    |
| `quit`     | Exits the app                                         |

---

## RAG Pipeline — How It Works

```
INGESTION (once)
  PDF → extract text (pypdf)
      → split into 500-char chunks with 50-char overlap
      → embed each chunk (sentence-transformers, local)
      → store vectors + text + page metadata (ChromaDB)

QUERY (every question)
  User question → embed (same model)
                → similarity search → top 4 chunks (ChromaDB)
                → build prompt: system + chunks + question
                → send to Claude (claude-3-5-haiku)
                → return answer with page citations
```

---

## What Is and Isn't Committed

| Committed ✅         | Not committed ❌                        |
|---------------------|-----------------------------------------|
| `rag.py`            | `venv/` (regenerate with pip install)   |
| `ingest.py`         | `chroma_db/` (regenerate with ingest)   |
| `query.py`          | `*.pdf` (user data)                     |
| `requirements.txt`  | `.env` / API keys                       |
| `CLAUDE.md`         |                                         |
| `.gitignore`        |                                         |

---

## Planned Increments

- [ ] Streamlit UI — browser-based interface with file upload
- [ ] Multi-PDF support with metadata filtering
- [ ] Conversation memory for follow-up questions
- [ ] Evals — measure retrieval quality and answer accuracy

---

## Repository

**GitHub:** https://github.com/Abhi-2016/pdf-rag
**Author:** Abhi-2016
**Co-author:** Claude Sonnet 4.6
