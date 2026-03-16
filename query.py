# query.py
# PURPOSE: Take a user question, find relevant chunks, ask Claude, return answer.
# Requires ingest.py to have been run first (so ChromaDB exists).

import anthropic
import chromadb
from sentence_transformers import SentenceTransformer

# ── Config ───────────────────────────────────────────────────────
DB_PATH  = "./chroma_db"
MODEL    = "claude-haiku-4-5"   # fast + cheap, great for Q&A
TOP_K    = 4                             # how many chunks to retrieve
# ─────────────────────────────────────────────────────────────────


def load_resources():
    """Load embedding model, ChromaDB collection, and Claude client."""
    print("⏳ Loading resources...")

    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    chroma_client = chromadb.PersistentClient(path=DB_PATH)
    collection    = chroma_client.get_collection("pdf_chunks")

    claude_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    print(f"✅ Ready  (collection has {collection.count()} chunks)\n")
    return embed_model, collection, claude_client


def retrieve(question, embed_model, collection):
    """
    Embed the question using the SAME model used during ingestion.
    ChromaDB compares it against all stored vectors and returns the
    TOP_K most semantically similar chunks.

    Distance: lower = more similar (ChromaDB uses L2 by default)
    """
    q_vector = embed_model.encode([question]).tolist()

    results = collection.query(
        query_embeddings = q_vector,
        n_results        = TOP_K,
        include          = ["documents", "metadatas", "distances"]
    )

    chunks    = results["documents"][0]   # list of raw text strings
    metadatas = results["metadatas"][0]   # list of {"page": N}
    distances = results["distances"][0]   # list of floats

    return chunks, metadatas, distances


def build_prompt(question, chunks, metadatas):
    """
    Construct the final prompt that gets sent to Claude.

    This is the KEY step of RAG — we inject the retrieved chunks
    as context so Claude can answer based on your document, not
    just its training data.
    """
    context_sections = []
    for chunk, meta in zip(chunks, metadatas):
        context_sections.append(f"[Page {meta['page']}]\n{chunk}")

    context = "\n\n---\n\n".join(context_sections)

    prompt = f"""You are a helpful assistant. Answer the user's question
using ONLY the context provided below.

Rules:
- Always cite which page(s) your answer comes from
- If the answer is not found in the context, say exactly:
  "I couldn't find that in the document."
- Do not make up or infer information beyond what is in the context

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

    return prompt


def ask_claude(prompt, claude_client):
    """Send the prompt to Claude and return the text response."""
    message = claude_client.messages.create(
        model     = MODEL,
        max_tokens= 1024,
        messages  = [{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def rag_query(question, embed_model, collection, claude_client):
    """Full RAG pipeline: retrieve → build prompt → ask Claude."""
    print(f"🔍 Retrieving chunks for: '{question}'")

    chunks, metadatas, distances = retrieve(question, embed_model, collection)

    pages_found = [m["page"] for m in metadatas]
    print(f"📄 Top chunks from pages: {pages_found}")
    print(f"📏 Similarity distances:  {[round(d, 3) for d in distances]}\n")

    prompt = build_prompt(question, chunks, metadatas)
    answer = ask_claude(prompt, claude_client)

    return answer


if __name__ == "__main__":
    embed_model, collection, claude_client = load_resources()

    print("💬 PDF Q&A — Type 'quit' to exit")
    print("─" * 60)

    while True:
        question = input("\nYour question: ").strip()

        if question.lower() == "quit":
            print("👋 Goodbye!")
            break
        if not question:
            continue

        answer = rag_query(question, embed_model, collection, claude_client)

        print(f"\n🤖 Claude:\n{answer}")
        print("\n" + "─" * 60)
