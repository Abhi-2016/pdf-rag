# ingest.py
# PURPOSE: Read a PDF, chunk it, embed it, and store in ChromaDB
# Run this once per PDF, or re-run whenever your PDF changes.

import pypdf
import chromadb
from sentence_transformers import SentenceTransformer

# ── Config (tweak these to experiment) ──────────────────────────
PDF_PATH  = "your_doc.pdf"   # <-- change to your PDF filename
DB_PATH   = "./chroma_db"    # local folder where vectors are saved
CHUNK_SZ  = 500              # characters per chunk
OVERLAP   = 50               # overlap between chunks
# ────────────────────────────────────────────────────────────────


def load_pdf(filepath):
    """
    Extract text from every page of the PDF.
    Returns a list of dicts: [{text, page}, ...]
    """
    reader = pypdf.PdfReader(filepath)
    pages = []

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append({
                "text": text,
                "page": page_num + 1
            })

    print(f"✅ Loaded {len(pages)} pages from '{filepath}'")
    return pages


def chunk_text(pages):
    """
    Split each page's text into smaller overlapping chunks.

    Why chunk?
      - LLMs have limited context windows
      - Smaller chunks = more precise retrieval
      - We only inject the *relevant* chunks, not the whole doc

    Why overlap?
      - Prevents sentences being cut off at chunk boundaries
      - A key sentence near the end of chunk N also appears
        at the start of chunk N+1
    """
    chunks = []

    for page_data in pages:
        text     = page_data["text"]
        page_num = page_data["page"]
        start    = 0

        while start < len(text):
            chunk_text = text[start : start + CHUNK_SZ]

            if chunk_text.strip():
                chunks.append({
                    "text":     chunk_text,
                    "page":     page_num,
                    "chunk_id": len(chunks)
                })

            # Advance by (chunk_size - overlap) so chunks overlap
            start += CHUNK_SZ - OVERLAP

    print(f"✅ Created {len(chunks)} chunks  "
          f"(chunk_size={CHUNK_SZ}, overlap={OVERLAP})")
    return chunks


def embed_and_store(chunks):
    """
    1. Load a local embedding model (downloads once, ~80MB)
    2. Convert each chunk's text into a vector
    3. Save vectors + text + metadata into ChromaDB on disk

    SentenceTransformer runs 100% locally — no API cost.
    'all-MiniLM-L6-v2' is small, fast, and good quality.
    """
    print("⏳ Loading embedding model (first run downloads ~80MB)...")
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    texts = [c["text"] for c in chunks]

    print("⏳ Embedding chunks...")
    embeddings = embed_model.encode(texts, show_progress_bar=True)

    # PersistentClient saves everything to disk at DB_PATH
    client = chromadb.PersistentClient(path=DB_PATH)

    # Fresh start — delete old collection if it exists
    try:
        client.delete_collection("pdf_chunks")
        print("🗑  Deleted old collection")
    except Exception:
        pass

    collection = client.create_collection("pdf_chunks")

    collection.add(
        ids        = [str(c["chunk_id"]) for c in chunks],
        embeddings = embeddings.tolist(),
        documents  = texts,
        metadatas  = [{"page": c["page"]} for c in chunks]
    )

    print(f"✅ Stored {len(chunks)} chunks in ChromaDB at '{DB_PATH}'\n")


if __name__ == "__main__":
    pages  = load_pdf(PDF_PATH)
    chunks = chunk_text(pages)
    embed_and_store(chunks)
    print("🎉 Ingestion complete! You can now run query.py or rag.py")
