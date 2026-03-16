# CLAUDE.md — PDF RAG Project

This file gives Claude Code context about this project so it can assist effectively.

---

## Project Overview

A **Claude-native Retrieval-Augmented Generation (RAG)** system that lets you chat with any PDF.
Built as a learning POC for an aspiring AI PM — no LangChain, everything wired from scratch so
each step is visible and understandable.

---

## Tech Stack

| Component       | Tool                          | Notes                                          |
|-----------------|-------------------------------|------------------------------------------------|
| LLM             | Claude (`claude-haiku-4-5`)   | Via Anthropic SDK — updated from deprecated haiku |
| Embeddings      | `sentence-transformers`       | Local model, no API cost                       |
| Embedding model | `all-MiniLM-L6-v2`            | ~80MB, downloads on first run                  |
| Vector DB       | ChromaDB (`PersistentClient`) | Stored locally in `./chroma_db/`               |
| PDF Parser      | `pypdf`                       | Pure Python, no system dependencies            |
| UI              | Streamlit                     | Browser-based app, runs at localhost:8501      |
| Env loading     | `python-dotenv`               | Loads `.env` inside the Streamlit process      |
| Python          | 3.9+                          | Managed via `venv`                             |

---

## Project Structure

```
pdf-rag/
├── app.py                  # Streamlit browser UI — PRIMARY ENTRY POINT
├── ingest.py               # Ingestion pipeline (run once per PDF)
├── query.py                # Terminal-based Q&A loop
├── rag.py                  # All-in-one terminal app
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml         # Forces light mode so custom CSS works correctly
├── README.md               # Public-facing project documentation
├── CLAUDE.md               # This file — context for Claude Code
├── .gitignore              # Excludes venv/, chroma_db/, *.pdf, .env, ~$*
├── venv/                   # Virtual environment (not committed)
└── chroma_db/              # Vector database on disk (not committed)
```

---

## Key Config Values

All tunable constants live at the top of each file:

| Variable   | File        | Default                  | Effect                                       |
|------------|-------------|--------------------------|----------------------------------------------|
| `PDF_PATH` | `ingest.py` | `"Slack Product FAQ.pdf"`| Path to the PDF to ingest                    |
| `DB_PATH`  | all files   | `"./chroma_db"`          | Where ChromaDB persists vectors              |
| `MODEL`    | `app.py`, `query.py` | `"claude-haiku-4-5"` | Claude model for generation         |
| `TOP_K`    | `app.py`    | `3`                      | Chunks retrieved per question in UI          |
| `TOP_K`    | `query.py`  | `4`                      | Chunks retrieved per question in terminal    |
| `CHUNK_SZ` | `ingest.py` | `500`                    | Characters per chunk (tuned for FAQ docs)    |
| `OVERLAP`  | `ingest.py` | `50`                     | Character overlap between adjacent chunks    |

---

## Environment Variables

Stored in `.env` in the project root (never committed to git):

```
ANTHROPIC_API_KEY=sk-ant-...
```

`app.py` loads this automatically via `load_dotenv()` — no need to `source .env` manually.
`query.py` and `rag.py` require `source .env` in the terminal before running.

---

## Setup

```bash
# 1. Clone and enter project
git clone https://github.com/Abhi-2016/pdf-rag.git && cd pdf-rag

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add API key to .env
echo 'ANTHROPIC_API_KEY=sk-ant-your-key-here' > .env
```

---

## Running the App

### Option A — Streamlit UI (recommended)
```bash
source venv/bin/activate
streamlit run app.py
```
- Opens at http://localhost:8501
- Loads `.env` automatically — no `source .env` needed
- Click a suggested question bubble or type your own
- Shows answer, source pages, and expandable raw chunks

### Option B — Terminal loop
```bash
source .env && source venv/bin/activate
python3 query.py
```

### Option C — All-in-one terminal app
```bash
source .env && source venv/bin/activate
python3 rag.py
# Commands: 'reingest', 'quit'
```

### Ingestion (always run this first, or when PDF changes)
```bash
source venv/bin/activate
python3 ingest.py
```

---

## Known Issues & Fixes Applied

| Issue | Root cause | Fix applied |
|---|---|---|
| `NotOpenSSLWarning` in terminal | macOS ships LibreSSL, not OpenSSL | `warnings.filterwarnings()` at top of `app.py` |
| API key not found in Streamlit | Streamlit spawns a new process that doesn't inherit `source .env` | `load_dotenv()` inside `app.py` via `python-dotenv` |
| Answer box invisible in dark mode | CSS `.answer-box` had no explicit text colour | Added `color: #1a1a1a` + switched to `st.info()` |
| Model deprecated error | `claude-3-5-haiku-20241022` reached end-of-life | Updated to `claude-haiku-4-5` across all files |

---

## RAG Pipeline — How It Works

```
INGESTION (once per PDF)
  PDF → extract text (pypdf)
      → split into 500-char chunks with 50-char overlap (ingest.py)
      → embed each chunk locally (sentence-transformers)
      → store vectors + text + page metadata (ChromaDB → ./chroma_db/)

QUERY (every question)
  User question → embed with same model
                → cosine similarity search → top 3-4 chunks (ChromaDB)
                → build prompt: instructions + chunks + question
                → send to Claude (claude-haiku-4-5)
                → return answer + page citations
```

---

## Streamlit UI Features

| Feature | Implementation |
|---|---|
| Suggested question bubbles | `st.button()` in `st.columns()`, writes to `st.session_state` |
| Bubble → text box population | `st.session_state.query` read by `st.text_input(value=...)` |
| Answer display | `st.info()` — handles dark/light mode automatically |
| Source page pills | Custom HTML/CSS via `st.markdown(unsafe_allow_html=True)` |
| Raw chunk debugger | `st.expander()` with chunk text and similarity distances |
| Resource caching | `@st.cache_resource` — loads embedding model once, not per click |

---

## What Is and Isn't Committed

| Committed ✅          | Not committed ❌                          |
|----------------------|------------------------------------------|
| `app.py`             | `venv/` (regenerate with pip install)    |
| `ingest.py`          | `chroma_db/` (regenerate with ingest)    |
| `query.py`           | `*.pdf` (user data)                      |
| `rag.py`             | `.env` (contains API key)                |
| `requirements.txt`   | `~$*` (Microsoft Office temp files)      |
| `README.md`          |                                          |
| `CLAUDE.md`          |                                          |
| `.gitignore`         |                                          |
| `.streamlit/config.toml` |                                      |

---

## Roadmap

- [x] Terminal RAG pipeline (`ingest.py` + `query.py` + `rag.py`)
- [x] Streamlit browser UI with suggested question bubbles
- [x] Source page citations
- [x] Debug chunk viewer with similarity distances
- [x] README and CLAUDE.md documentation
- [ ] PDF file uploader in the UI
- [ ] Multi-PDF support with metadata filtering
- [ ] Conversation memory for follow-up questions
- [ ] Confidence score indicator based on retrieval distance
- [ ] Evals — measure retrieval quality and answer accuracy

---

## Repository

**GitHub:** https://github.com/Abhi-2016/pdf-rag
**Author:** Abhi-2016
**Co-author:** Claude Sonnet 4.6
