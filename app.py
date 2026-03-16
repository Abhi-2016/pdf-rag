# app.py — Streamlit UI for PDF RAG
# Run with: streamlit run app.py

import warnings
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

import os
import anthropic
import chromadb
import streamlit as st
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()  # reads .env file and loads ANTHROPIC_API_KEY into os.environ

# ── Config ───────────────────────────────────────────────────────
DB_PATH = "./chroma_db"
MODEL   = "claude-haiku-4-5"
TOP_K   = 3

SUGGESTED_QUESTIONS = [
    "What is Slack?",
    "What does @here do vs @channel?",
    "How do I search for a file?",
    "Does Slack support 2FA?",
    "How do I set my status to Away?",
    "Can I use Slack offline?",
]
# ─────────────────────────────────────────────────────────────────


# ── Load resources once (cached so they don't reload on every interaction) ──
@st.cache_resource
def load_resources():
    embed_model   = SentenceTransformer("all-MiniLM-L6-v2")
    collection    = chromadb.PersistentClient(path=DB_PATH).get_collection("pdf_chunks")
    claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return embed_model, collection, claude_client


def rag_query(question, embed_model, collection, claude_client):
    """Full RAG pipeline: retrieve → build prompt → ask Claude."""
    results = collection.query(
        query_embeddings=embed_model.encode([question]).tolist(),
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"]
    )
    chunks    = results["documents"][0]
    metas     = results["metadatas"][0]
    distances = results["distances"][0]

    context = "\n\n---\n\n".join(
        f"[Page {m['page']}]\n{c}" for c, m in zip(chunks, metas)
    )

    prompt = f"""You are a helpful assistant answering questions about a product FAQ.
Answer using ONLY the context provided. Always cite which page the answer comes from.
If the answer is not in the context, say: "I couldn't find that in the document."

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

    msg = claude_client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )

    return msg.content[0].text, chunks, metas, distances


# ── Page config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="PDF RAG",
    page_icon="📄",
    layout="centered"
)

# ── Styling ──────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Question bubble buttons */
    div[data-testid="column"] button {
        background-color: #f0f2f6;
        border: 1px solid #d0d3da;
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 0.85rem;
        color: #333;
        width: 100%;
        transition: background-color 0.2s;
    }
    div[data-testid="column"] button:hover {
        background-color: #e0e3ea;
        border-color: #999;
    }

    /* Answer box */
    .answer-box {
        background-color: #f8f9fb;
        border-left: 4px solid #4a90d9;
        border-radius: 6px;
        padding: 16px 20px;
        margin-top: 16px;
        font-size: 0.95rem;
        line-height: 1.6;
        color: #1a1a1a;         /* explicit dark text — fixes dark mode conflict */
    }

    /* Source pills */
    .source-pill {
        display: inline-block;
        background-color: #eaf0fb;
        color: #2c5fa8;
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.78rem;
        margin-right: 6px;
        margin-top: 8px;
    }

    /* Hide Streamlit default footer */
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Header ───────────────────────────────────────────────────────
st.title("📄 PDF RAG")
st.caption("Ask questions about your document — powered by Claude")
st.divider()


# ── Load resources ───────────────────────────────────────────────
try:
    embed_model, collection, claude_client = load_resources()
except Exception as e:
    st.error(f"❌ Could not load database. Have you run `python3 ingest.py` first?\n\n`{e}`")
    st.stop()


# ── Session state — tracks the active question in the text box ──
if "query" not in st.session_state:
    st.session_state.query = ""


# ── Suggested question bubbles ───────────────────────────────────
st.markdown("**Try asking:**")

# Lay bubbles out in rows of 3
cols_per_row = 3
for row_start in range(0, len(SUGGESTED_QUESTIONS), cols_per_row):
    row_questions = SUGGESTED_QUESTIONS[row_start : row_start + cols_per_row]
    cols = st.columns(len(row_questions))
    for col, question in zip(cols, row_questions):
        with col:
            if st.button(question, key=f"bubble_{question}"):
                st.session_state.query = question

st.divider()


# ── Text input ───────────────────────────────────────────────────
user_input = st.text_input(
    label="Your question",
    value=st.session_state.query,
    placeholder="Type a question or click a bubble above...",
    label_visibility="collapsed"
)

ask_clicked = st.button("Ask →", type="primary", use_container_width=False)


# ── Run RAG when question is submitted ───────────────────────────
question = user_input.strip()

if ask_clicked and question:
    with st.spinner("Searching document and asking Claude..."):
        try:
            answer, chunks, metas, distances = rag_query(
                question, embed_model, collection, claude_client
            )

            # Answer — st.info() handles dark/light mode automatically
            st.info(answer)

            # Source pages
            pages = sorted(set(m["page"] for m in metas))
            pills = "".join(f'<span class="source-pill">Page {p}</span>' for p in pages)
            st.markdown(f"<div style='margin-top:8px'>Sources: {pills}</div>", unsafe_allow_html=True)

            # Expandable: show raw retrieved chunks
            with st.expander("🔍 View retrieved chunks"):
                for i, (chunk, meta, dist) in enumerate(zip(chunks, metas, distances)):
                    st.markdown(f"**Chunk {i+1} — Page {meta['page']} — distance: `{round(dist, 3)}`**")
                    st.text(chunk)
                    st.divider()

        except Exception as e:
            st.error(f"Something went wrong: {e}")

elif ask_clicked and not question:
    st.warning("Please enter a question first.")
