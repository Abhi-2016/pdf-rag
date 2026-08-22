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
| Enter key didn't submit | Plain `st.button` only responds to click | Wrapped input + button in `st.form` |

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
                → build prompt:
                    [system instructions]
                    [conversation history — last 5 turns]   ← memory
                    [retrieved chunks — current question]   ← retrieval
                    [current question]
                → send to Claude (claude-haiku-4-5)
                → return answer + page citations
                → save turn to st.session_state.history
```

---

## Streamlit UI Features

| Feature | Implementation |
|---|---|
| Suggested question bubbles | `st.button()` in `st.columns()`, writes to `st.session_state` |
| Bubble → text box population | `st.session_state.query` read by `st.text_input(value=...)` |
| Enter to send | `st.form` wrapping input + button — Enter submits the form |
| Auto-clear input | `clear_on_submit=True` on `st.form` wipes input after submit |
| Conversation memory | `st.session_state.history` list of `{question, answer, pages}` turns |
| History in prompt | `build_history_text()` formats last 5 turns, injected before question |
| Chat bubble UI | Custom HTML/CSS floated divs — user right, Claude left |
| Clear conversation | `🗑 Clear` button resets `history` and `query` in session state |
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
| `docs/screenshot.png`|                                          |

---

## Advanced RAG Course — Working Agreement

This project now doubles as a structured learning course. The following rules govern all module work.

### Ground Rules
1. PLAN.md, CLAUDE.md, and README.md updated after every module commit
2. Every module on its own branch, merged to main when complete
3. User drives all decisions — Claude explains and guides, user approves before any code is written
4. Evals built for every module, not deferred
5. Claude explains the concept being practised before any code is written
6. For PM exercises (eval design, architecture decisions), Claude asks questions — user builds the answer — Claude does not generate output unprompted
7. Honest, direct feedback — Claude pushes back when something is underdeveloped or wrong

### Learning Tracker

| Module | Architecture | Status | Branch | Key Concepts |
|---|---|---|---|---|
| 1 | Corrective RAG (CRAG) | 🔲 Not started | `module/crag` | LLM-as-judge, query rewriting, fallback design |
| 2 | Hybrid RAG | 🔲 Not started | `module/hybrid-rag` | BM25, sparse+dense, Reciprocal Rank Fusion |
| 3 | Agentic RAG | 🔲 Not started | `module/agentic-rag` | Tool-use loop, planner agent, multi-strategy retrieval |
| 4 | Multimodal RAG | 🔲 Not started | `module/multimodal-rag` | ColPali/CLIP, vision LLM, unified vector index |
| 5 | GraphRAG | 🔲 Not started | `module/graphrag` | Knowledge graph, entity extraction, community summaries |

### AI PM Concepts Tracker

| Concept | Module | Status |
|---|---|---|
| Failure mode identification | CRAG | 🔲 |
| Fallback design | CRAG | 🔲 |
| Eval-driven iteration | CRAG | 🔲 |
| Complementary system design | Hybrid RAG | 🔲 |
| Latency vs. accuracy tradeoff | Hybrid RAG | 🔲 |
| Agentic vs. pipeline architecture decision | Agentic RAG | 🔲 |
| Agent loop design | Agentic RAG | 🔲 |
| Use case scoping for multimodal | Multimodal RAG | 🔲 |
| Vision model cost architecture | Multimodal RAG | 🔲 |
| Preprocessing vs. query-time tradeoff | GraphRAG | 🔲 |
| When graph structure is worth the cost | GraphRAG | 🔲 |

---

## Key Wrong Calls & Corrections

Decisions that didn't work, what broke, and the fix applied. Split into technical and AI PM calls.

### Technical

| # | Wrong Call | What Broke | Fix Applied |
|---|---|---|---|
| 1 | `source .env` for API key in Streamlit | Streamlit spawns a subprocess — doesn't inherit shell env | `load_dotenv()` inside `app.py` via `python-dotenv` |
| 2 | Custom `.answer-box` CSS without explicit text colour | Answer invisible in dark mode | Switched to `st.info()` — handles theming automatically |
| 3 | Hardcoded `claude-3-5-haiku-20241022` model ID | API deprecation error on every call | Updated to `claude-haiku-4-5` across all files |
| 4 | Plain `st.button` for question submission | Enter key doesn't trigger `st.button` — click only | Wrapped in `st.form(clear_on_submit=True)` |
| 5 | CSS assumed light background; locked app to light mode | Dark mode entirely broken for injected HTML | Locked via `.streamlit/config.toml` (documented workaround, not a real fix) |
| 6 | LibreSSL warning not suppressed | Noisy terminal output on every run | `warnings.filterwarnings()` at module level for that specific warning |
| 7 | Generic chunk size not tuned for document type | Poor retrieval on FAQ-style docs | Tuned `CHUNK_SZ=500`, `OVERLAP=50` for FAQ content |

### AI PM

| # | Wrong Call | What Broke | Fix Applied |
|---|---|---|---|
| 8 | Documentation written after the code | Architectural decisions lost; README arrived at commit 5, PLAN.md at commit 13 | For future projects: CLAUDE.md + PLAN.md at commit 1 |
| 9 | Evals deferred to phase 4 — never built | No way to measure if retrieval or generation actually works | Eval now explicitly split into two axes: retrieval quality + answer accuracy |
| 10 | `CHUNK_SZ` changed globally for TSLA 10-K (500→2000) | FAQ retrieval degraded silently — one config, two document types | Per-document chunk config needed; multi-PDF support will force this |
| 11 | README promised "chat with any PDF" but PDF path was hardcoded | Product promise vs. actual capability misaligned from day one | File uploader on roadmap; interim fix: named constant at top of `ingest.py` |

---

## Architecture Decisions

Full decision log — what was decided, and why. 24 decisions across LLM, retrieval, UI, pipeline, and documentation.

| Decision Area | What the Decision Was | Why It Was Made |
|---|---|---|
| **LLM choice** | `claude-haiku-4-5`, not Sonnet or Opus | Fast and cheap for Q&A over retrieved chunks; Sonnet available as a named upgrade path |
| **Model ID format** | Alias string (`claude-haiku-4-5`), not a versioned ID | Version-pinned IDs reach end-of-life silently; aliases survive model updates without code changes |
| **Embedding provider** | `sentence-transformers` locally, not an API-based service | Zero API cost; runs on-device; no network call per ingestion |
| **Embedding model** | `all-MiniLM-L6-v2` (~80MB) | Fast, accurate enough for retrieval, reasonable one-time download |
| **Embedding consistency** | Same model for both ingestion and query | Different models produce incompatible vector spaces — mismatch makes similarity scores meaningless |
| **Vector DB** | ChromaDB `PersistentClient`, not Pinecone or Weaviate | No server; persists to disk between sessions; simple Python API; right-sized for a POC |
| **Vector storage** | `./chroma_db/` on disk, gitignored | User data; regenerated by `ingest.py`; out of git keeps the repo clean and portable |
| **Chunk size** | 500 chars (tuned from generic, and from 2000 after TSLA 10-K test) | FAQ-style docs have short discrete answers — smaller chunks = more precise retrieval |
| **Overlap** | 50 chars (~10% of chunk size) | Prevents concepts split at boundaries from being lost without significantly duplicating content |
| **TOP_K** | 3 in UI, 4 in terminal | Balances context richness vs. token cost; more chunks dilute the prompt if irrelevant |
| **Memory window** | Last 5 turns injected into prompt | Enough to resolve follow-up references without excessive token cost per query |
| **Framework** | No LangChain — built from scratch | Transparency over velocity; learning POC requires every layer to be visible and explainable |
| **PDF parser** | `pypdf`, not PyMuPDF or pdfplumber | Lightweight, pure Python, no system-level dependencies |
| **UI framework** | Streamlit, not Flask/FastAPI/Next.js | Minimal boilerplate; avoids frontend complexity for a POC |
| **Form submission** | `st.form`, not plain `st.button` | `st.button` only responds to click; `st.form` captures Enter key and clears input on submit |
| **Answer display** | `st.info()`, not a custom CSS div | Native component handles light/dark theming automatically |
| **Theme** | Locked to light mode via `.streamlit/config.toml` | Custom HTML/CSS bypasses Streamlit's theme system; workaround, not a permanent fix |
| **Embedding model caching** | `@st.cache_resource` on the model loader | Without caching, the 80MB model reloads on every Streamlit rerun |
| **API key loading** | `load_dotenv()` inside `app.py`, not `source .env` | Streamlit spawns a subprocess that doesn't inherit the parent shell's environment |
| **Config constants** | Named constants at the top of each file | Makes tuning changes one-line edits per file, not string hunts across the codebase |
| **Pipeline structure** | Separate `ingest.py` / `query.py` / `app.py`, each independently runnable | Separates concerns — ingestion runs once, query runs per session, UI wraps both |
| **Documentation split** | CLAUDE.md (internal) vs README.md (public-facing) | Different audiences: CLAUDE.md for developers/AI collaborators; README for recruiters/reviewers |
| **PLAN.md** | Created retroactively at commit 13 | Decisions weren't captured upfront; records the "why" for future contributors |
| **Wrong calls split** | Technical and AI PM as separate categories | Engineers care about technical fixes; PMs care about product and process decisions |

---

## AI PM Concepts Demonstrated

This project was built as an AI PM portfolio piece. The decisions below map to PM thinking, not just engineering.

| Concept | Decision Made | Why It Matters as a PM |
|---|---|---|
| Build vs. Buy | Skipped LangChain; wired everything from scratch | Transparency over velocity — every layer is explainable to a stakeholder |
| POC Scoping | Shipped core pipeline + UI first; deferred multi-PDF, uploader, evals | Defines MVP boundary; roadmap carries the rest without scope creep |
| AI Strategy Selection | Chose RAG over fine-tuning, map-reduce, full-context | Match the technique to the constraint — doc size, citation need, data freshness |
| Cost Architecture | Local embeddings (free) + Haiku (cheapest tier) | Embed cost and generation cost are separate levers — design both intentionally |
| Trust & Explainability UX | Page citations + debug chunk expander with similarity distances | Users distrust AI answers they can't verify — citations are a trust primitive |
| Hallucination Mitigation | System prompt constrains Claude to only answer from retrieved chunks | Grounding reduces hallucination; evals measure how well — can't skip either |
| Evaluation Planning | Evals on roadmap: retrieval quality + answer accuracy as separate axes | A retrieval failure and a generation failure need completely different fixes |
| Documentation as Product Artifact | CLAUDE.md (internal) + README.md (public) written alongside the code | CLAUDE.md encodes decisions that git history alone won't surface |

---

## Roadmap

- [x] Terminal RAG pipeline (`ingest.py` + `query.py` + `rag.py`)
- [x] Streamlit browser UI with suggested question bubbles
- [x] Source page citations
- [x] Debug chunk viewer with similarity distances
- [x] README and CLAUDE.md documentation
- [x] Conversation memory — last 5 turns injected into prompt
- [x] Chat bubble UI — user right, Claude left, Clear button
- [x] Enter-to-send and auto-clear input (`st.form`)
- [ ] PDF file uploader in the UI
- [ ] Multi-PDF support with metadata filtering
- [ ] Confidence score indicator based on retrieval distance
- [ ] Evals — measure retrieval quality and answer accuracy

---

## Repository

**GitHub:** https://github.com/Abhi-2016/pdf-rag
**Author:** Abhi-2016
**Co-author:** Claude Sonnet 4.6
