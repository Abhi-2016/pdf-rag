# rag.py
# PURPOSE: All-in-one RAG app. Auto-ingests if DB doesn't exist,
#          then drops straight into the Q&A loop.
#
# Usage:
#   1. Set PDF_PATH below to your PDF filename
#   2. Run: python rag.py
#   3. Ask questions!
#
# Commands while chatting:
#   reingest  → reload and re-embed the PDF (use after changing PDF)
#   chunks    → show raw chunks for your last question (debug)
#   quit      → exit

import os
import warnings
warnings.filterwarnings("ignore", category=Warning)  # suppress LibreSSL noise

# Auto-load .env file if it exists
def _load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    k, v = key.strip(), value.strip()
                    if not os.environ.get(k):  # set if missing or empty
                        os.environ[k] = v
_load_env()

import pypdf
import chromadb
import anthropic
from sentence_transformers import SentenceTransformer

# ── Config — edit these ──────────────────────────────────────────
PDF_PATH  = "nasdaq-tsla-2026-10K-26574326.pdf"   # <-- your PDF filename
DB_PATH   = "./chroma_db"
MODEL     = "claude-haiku-4-5"
TOP_K     = 4       # chunks to retrieve per question
CHUNK_SZ  = 500     # characters per chunk
OVERLAP   = 50      # overlap between chunks
# ─────────────────────────────────────────────────────────────────


# ── Ingestion ────────────────────────────────────────────────────

def load_and_chunk(filepath):
    reader = pypdf.PdfReader(filepath)
    chunks = []

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not (text and text.strip()):
            continue
        start = 0
        while start < len(text):
            chunk = text[start : start + CHUNK_SZ]
            if chunk.strip():
                chunks.append({
                    "text": chunk,
                    "page": page_num + 1,
                    "id":   len(chunks)
                })
            start += CHUNK_SZ - OVERLAP

    print(f"✅ {len(chunks)} chunks from {filepath}")
    return chunks


def build_db(chunks, embed_model, client):
    print("⏳ Embedding and storing chunks...")
    embeddings = embed_model.encode(
        [c["text"] for c in chunks], show_progress_bar=True
    )

    try:
        client.delete_collection("pdf_chunks")
    except Exception:
        pass

    col = client.create_collection("pdf_chunks")
    col.add(
        ids        = [str(c["id"])   for c in chunks],
        embeddings = embeddings.tolist(),
        documents  = [c["text"]      for c in chunks],
        metadatas  = [{"page": c["page"]} for c in chunks]
    )
    print(f"✅ Database ready — {len(chunks)} chunks stored\n")
    return col


# ── Query ────────────────────────────────────────────────────────

def retrieve(question, embed_model, collection):
    q_vec = embed_model.encode([question]).tolist()
    results = collection.query(
        query_embeddings = q_vec,
        n_results        = TOP_K,
        include          = ["documents", "metadatas", "distances"]
    )
    return (
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    )


def build_prompt(question, chunks, metadatas):
    context = "\n\n---\n\n".join(
        f"[Page {m['page']}]\n{c}"
        for c, m in zip(chunks, metadatas)
    )
    return f"""You are a helpful assistant. Answer using ONLY the context below.
Always cite the page number(s). If not found, say "I couldn't find that in the document."

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


# ── Main app ─────────────────────────────────────────────────────

def main():
    # Check API key early
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set.")
        print("   Run: export ANTHROPIC_API_KEY='sk-ant-...'")
        return

    # Check PDF exists
    if not os.path.exists(PDF_PATH):
        print(f"❌ PDF not found: '{PDF_PATH}'")
        print(f"   Add your PDF to this folder and update PDF_PATH in rag.py")
        return

    print("⏳ Loading embedding model...")
    embed_model   = SentenceTransformer("all-MiniLM-L6-v2")
    chroma_client = chromadb.PersistentClient(path=DB_PATH)
    claude_client = anthropic.Anthropic()

    # Auto-ingest if DB doesn't exist
    try:
        collection = chroma_client.get_collection("pdf_chunks")
        print(f"✅ Loaded existing database ({collection.count()} chunks)")
    except Exception:
        print(f"📄 No database found — ingesting '{PDF_PATH}'...")
        chunks     = load_and_chunk(PDF_PATH)
        collection = build_db(chunks, embed_model, chroma_client)

    print(f"\n💬 Chatting about: {PDF_PATH}")
    print("Commands: 'reingest' | 'chunks' | 'quit'")
    print("─" * 60 + "\n")

    last_chunks   = []
    last_metadatas= []

    while True:
        question = input("You: ").strip()

        if not question:
            continue

        # ── Special commands ──
        if question.lower() == "quit":
            print("👋 Goodbye!")
            break

        if question.lower() == "reingest":
            print(f"🔄 Re-ingesting '{PDF_PATH}'...")
            chunks     = load_and_chunk(PDF_PATH)
            collection = build_db(chunks, embed_model, chroma_client)
            continue

        if question.lower() == "chunks":
            if not last_chunks:
                print("  (No previous query yet)\n")
            else:
                print("\n── Retrieved chunks from last query ──")
                for i, (c, m) in enumerate(zip(last_chunks, last_metadatas)):
                    print(f"\n[Chunk {i+1} | Page {m['page']}]\n{c}")
                print("─" * 40 + "\n")
            continue

        # ── RAG query ──
        chunks, metadatas, distances = retrieve(question, embed_model, collection)
        last_chunks    = chunks
        last_metadatas = metadatas

        pages = [m["page"] for m in metadatas]
        print(f"  (Retrieved from pages: {pages})\n")

        prompt  = build_prompt(question, chunks, metadatas)
        message = claude_client.messages.create(
            model      = MODEL,
            max_tokens = 1024,
            messages   = [{"role": "user", "content": prompt}]
        )

        answer = message.content[0].text
        print(f"Claude: {answer}\n")
        print("─" * 60 + "\n")


if __name__ == "__main__":
    main()
