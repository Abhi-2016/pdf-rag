# 📄 PDF RAG — Chat with Your Documents

A **Claude-native Retrieval-Augmented Generation (RAG)** system that lets you ask questions about any PDF and get grounded, cited answers. Built from scratch as a learning POC — no LangChain, every step is visible and explained.

> Built by [Abhi-2016](https://github.com/Abhi-2016) · Powered by [Claude](https://anthropic.com) · Co-authored with Claude Sonnet 4.6

---

## What It Does

Upload any PDF, ask questions in plain English, and get answers grounded in the document — with page citations and source chunk visibility.

![PDF RAG UI](https://github.com/Abhi-2016/pdf-rag/raw/main/docs/screenshot.png)

---

## How It Works

```
INGESTION (run once per PDF)
  PDF → extract text → split into chunks → embed → store in ChromaDB

QUERY (every question)
  Question → embed → similarity search → top chunks → Claude → answer

CONVERSATION MEMORY
  Each Q&A turn is stored in session state → injected into the next
  prompt so Claude can resolve follow-ups like "tell me more" or "it"
```

The system never makes up answers. If something isn't in the document, it says so.

---

## Tech Stack

| Component | Tool | Why |
|---|---|---|
| LLM | Claude (`claude-haiku-4-5`) | Fast, cheap, great for Q&A |
| Embeddings | `sentence-transformers` (local) | Free, no API cost, runs on your machine |
| Vector DB | ChromaDB | Local, persists to disk, no server needed |
| PDF Parser | pypdf | Lightweight, pure Python |
| UI | Streamlit | Browser-based app with zero HTML/JS |

---

## Project Structure

```
pdf-rag/
├── app.py              # Streamlit browser UI — START HERE
├── ingest.py           # Ingestion pipeline (run once per PDF)
├── query.py            # Terminal-based Q&A loop
├── rag.py              # Combined all-in-one terminal app
├── requirements.txt    # Python dependencies
├── .streamlit/
│   └── config.toml     # Streamlit theme config
├── CLAUDE.md           # Project context for Claude Code
├── .gitignore
└── chroma_db/          # Vector database (auto-generated, not committed)
```

---

## Quickstart

### 1. Clone the repo
```bash
git clone https://github.com/Abhi-2016/pdf-rag.git
cd pdf-rag
```

### 2. Create and activate a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your Anthropic API key
Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```
> Get your API key at [console.anthropic.com](https://console.anthropic.com)

### 5. Add your PDF
Drop any text-based PDF into the project folder.

### 6. Ingest the PDF
```bash
python3 ingest.py
```
This reads your PDF, chunks it, embeds it, and saves it to ChromaDB. Run once per PDF.

### 7. Launch the UI
```bash
streamlit run app.py
```
Opens at [http://localhost:8501](http://localhost:8501)

---

## Usage

**Browser UI (`app.py`)**
- Click a suggested question bubble or type your own
- Press **Enter** or click **Ask →** to send — no mouse required
- Input auto-clears after each submission
- Ask follow-up questions — the app remembers the full conversation
- Click **🗑 Clear** to start a fresh conversation
- View source page citations and expand raw chunks for debugging

**Terminal (`query.py`)**
```bash
python3 query.py
```

**All-in-one (`rag.py`)**
```bash
python3 rag.py
# Type 'reingest' to reload the PDF, 'quit' to exit
```

---

## Configuration

All tuning knobs live at the top of each file:

| Variable | Default | Effect |
|---|---|---|
| `PDF_PATH` | `"your_doc.pdf"` | Path to your PDF |
| `CHUNK_SZ` | `500` | Characters per chunk — smaller = more precise retrieval |
| `OVERLAP` | `50` | Overlap between chunks — prevents boundary cutoffs |
| `TOP_K` | `3` | Chunks retrieved per question — more = more context |
| `MODEL` | `claude-haiku-4-5` | Claude model — swap for `claude-sonnet-4-5` for harder reasoning |

---

## What PDFs Work Best

| Works well ✅ | Doesn't work ❌ |
|---|---|
| Text-based PDFs | Scanned / image PDFs |
| FAQ documents | Password-protected PDFs |
| Reports & whitepapers | Heavily table-based docs |
| Product documentation | Handwritten documents |
| Academic papers | |

> **Tip:** Test if your PDF is readable: `python3 -c "import pypdf; print(pypdf.PdfReader('your.pdf').pages[0].extract_text()[:200])"`

---

## RAG vs Other Approaches

| Approach | When to use |
|---|---|
| **RAG** (this project) | Large private docs, need citations, data changes often |
| **Send full doc to Claude** | Short docs under 100k tokens |
| **Fine-tuning** | Consistent style/tone, not factual recall |
| **Map-reduce** | Full-doc summarisation |

---

## Roadmap

- [x] Terminal-based RAG pipeline
- [x] Streamlit browser UI
- [x] Suggested question bubbles
- [x] Source page citations
- [x] Debug chunk viewer
- [x] Conversation memory (follow-up questions with context)
- [x] Enter-to-send and auto-clear input
- [ ] PDF file uploader in the UI
- [ ] Multi-PDF support
- [ ] Confidence score indicator
- [ ] Evals — measure retrieval and answer quality

---

## Requirements

- Python 3.9+
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- ~200MB disk space (embedding model downloads on first run)

---

## License

MIT
