# PLAN.md — PDF RAG

Project plan, architecture decisions, and phase tracking. Updated alongside each commit.

---

## Goal

Build a Claude-native RAG system from scratch — no LangChain, every step visible — as a portfolio piece demonstrating AI PM thinking through real implementation.

---

## Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| LLM | Claude `claude-haiku-4-5` | Fast, cheap, strong at Q&A; swap to Sonnet for harder reasoning |
| Embeddings | `sentence-transformers` (local) | Zero API cost; `all-MiniLM-L6-v2` is fast and accurate for retrieval |
| Vector DB | ChromaDB (local, persistent) | No server required; persists to disk; simple Python API |
| PDF Parser | pypdf | Lightweight, pure Python, no system dependencies |
| UI | Streamlit | Browser-based, minimal boilerplate, good enough for a POC |
| Framework | None (from scratch) | Transparency over velocity — every layer must be explainable |

---

## Phases

### Phase 1 — Terminal Pipeline ✅
- `ingest.py`: PDF → chunks → embeddings → ChromaDB
- `query.py`: question → embed → search → Claude → answer
- `rag.py`: all-in-one terminal loop with `reingest` command

### Phase 2 — Streamlit UI ✅
- Browser-based chat interface at `localhost:8501`
- Suggested question bubbles, Enter-to-send, auto-clear input
- Source page citations and debug chunk expander
- Chat bubble UI (user right, Claude left)

### Phase 3 — Conversation Memory ✅
- Last 5 turns stored in `st.session_state.history`
- `build_history_text()` formats history and injects into each prompt
- Allows follow-up questions to resolve references ("it", "tell me more")

### Phase 4 — Evals 🔲
- Retrieval eval: are the right chunks surfaced for a given question?
- Answer eval: is Claude's generation factually correct given the context?
- These are separate axes — a retrieval failure and a generation failure need different fixes

### Phase 5 — Multi-PDF Support 🔲
- PDF file uploader in the UI (drag-and-drop)
- ChromaDB collection per document or metadata-filtered single collection
- Confidence score indicator based on retrieval distance

---

## Key Tradeoffs

**Chunk size (500 chars):** Tuned for FAQ-style docs. Smaller = more precise retrieval. Larger = more context per chunk but noisier matches. Adjust `CHUNK_SZ` in `ingest.py` and re-ingest.

**TOP_K (3 in UI, 4 in terminal):** More chunks = more context for Claude but higher token cost and risk of irrelevant content diluting the prompt.

**Memory window (5 turns):** Balances follow-up resolution against token cost. Increase `HISTORY_TURNS` in `app.py` for longer sessions.

**Haiku vs. Sonnet:** Haiku handles Q&A over retrieved chunks well. Switch `MODEL` to `claude-sonnet-4-5` in `app.py` if reasoning quality needs to improve.

---

## Retrospective — Wrong Calls & Corrections

Decisions that didn't work and what was learned. Kept here so future work on this project doesn't repeat them.

### Technical
| Wrong Call | Root Cause | Fix |
|---|---|---|
| `source .env` for API key | Streamlit spawns a subprocess; shell env not inherited | `load_dotenv()` inside `app.py` |
| Answer box invisible in dark mode | Custom CSS with no explicit text colour | Switched to `st.info()` (theme-aware native component) |
| Deprecated model ID `claude-3-5-haiku-20241022` | Hard-coded version string across three files | Updated to `claude-haiku-4-5`; use named `MODEL` constant per file |
| Enter key didn't submit | `st.button` only responds to click | Wrapped in `st.form(clear_on_submit=True)` |
| CSS broke in dark mode | Injected HTML bypasses Streamlit's theme system | Locked to light mode (workaround); real fix = CSS custom properties |
| Noisy LibreSSL warning | macOS ships LibreSSL, not OpenSSL | `warnings.filterwarnings()` scoped to that specific category |
| Chunk size not tuned | Started with a generic value before testing on actual doc | 500 chars / 50 overlap tuned for FAQ-style content |

### AI PM
| Wrong Call | What Broke | Lesson |
|---|---|---|
| Documentation written after code | Architectural decisions not captured while fresh; PLAN.md created 13 commits in | Write CLAUDE.md + PLAN.md before or at first commit |
| Evals deferred to phase 4 | No way to measure retrieval or generation quality at any point | Minimal eval (known Q→expected chunk) belongs in phase 1 |
| Global chunk size changed for one doc type | TSLA 10-K needed 2000-char chunks; FAQ needed 500 — one config broke the other | Chunk config must be per-document or per-collection |
| README promised "any PDF"; system was hardcoded | Product promise vs. actual capability misaligned at launch | Scope the promise to match the product, or build the uploader in phase 1 |

---

## What Is Not Committed

| Excluded | Reason |
|---|---|
| `venv/` | Regenerate with `pip install -r requirements.txt` |
| `chroma_db/` | Regenerate with `python3 ingest.py` |
| `*.pdf` | User data — not committed |
| `.env` | Contains API key |

---

## Roadmap

- [x] Terminal RAG pipeline
- [x] Streamlit browser UI
- [x] Suggested question bubbles
- [x] Source page citations
- [x] Debug chunk viewer with similarity distances
- [x] Conversation memory (last 5 turns)
- [x] Chat bubble UI + Clear button
- [x] Enter-to-send and auto-clear input
- [ ] PDF file uploader in the UI
- [ ] Multi-PDF support with metadata filtering
- [ ] Confidence score indicator
- [ ] Evals — retrieval quality + answer accuracy
