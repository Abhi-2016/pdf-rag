# crag.py — Corrective RAG orchestration layer
# Adds retrieval grading, query rewriting, and web fallback to the baseline pipeline.

MODEL = "claude-haiku-4-5"

GRADER_SYSTEM_PROMPT = """Your job as a judge is to grade retrieved chunks from a RAG system. You will have access to the user query also. You have to look at both these pieces of information and return -

1. Relevant - the retrieved chunk is a good match to or the retrieved chunk sufficiently answers the query being asked. You should return the phrase "RELEVANT"
2. Partial - the retrieved chunks are a somewhat match to the query, or it doesn't fully fit the query being asked. You should return the phrase "PARTIAL"
3. Irrelevant - if the retrieved chunk is not at all in any way a fit for the question being asked - then return the phrase "IRRELEVANT"

Grade each chunk independently and return one label per chunk."""

REWRITER_SYSTEM_PROMPT = """Your job as a query rewriter is as follows.
Some times a user will pose a vague or partially-matching question that results in poor or partial chunk or chunks retrieval.
In this scenario - you will receive this query. You should rewrite this question to be more specific and keyword rich. You must keep the original intent of the query when you rewrite it.
Return only the rewritten question, and nothing else."""


def _parse_grade(text):
    t = text.strip().upper()
    # Check IRRELEVANT before RELEVANT — "RELEVANT" is a substring of "IRRELEVANT"
    if "IRRELEVANT" in t:
        return "IRRELEVANT"
    if "RELEVANT" in t:
        return "RELEVANT"
    if "PARTIAL" in t:
        return "PARTIAL"
    return "IRRELEVANT"  # safe default when LLM returns unexpected text


def grade_chunks(question, chunks, claude_client):
    """Grade each chunk against the question. Returns list of RELEVANT/PARTIAL/IRRELEVANT."""
    grades = []
    for chunk in chunks:
        msg = claude_client.messages.create(
            model=MODEL,
            max_tokens=20,
            system=GRADER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Query: {question}\n\nChunk: {chunk}"}]
        )
        grades.append(_parse_grade(msg.content[0].text))
    return grades


def _best_grade(grades):
    if "RELEVANT" in grades:
        return "RELEVANT"
    if "PARTIAL" in grades:
        return "PARTIAL"
    return "IRRELEVANT"


def rewrite_query(question, claude_client):
    """Reformulate a vague question to improve retrieval."""
    msg = claude_client.messages.create(
        model=MODEL,
        max_tokens=200,
        system=REWRITER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}]
    )
    return msg.content[0].text.strip()


def web_search(question):
    """Fallback web search when local retrieval finds no relevant chunks."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(question, max_results=3))
        return "\n\n".join(r.get("body", "") for r in results)
    except Exception as e:
        return f"Web search unavailable: {e}"


def _build_prompt(question, chunks, metas, history_text=""):
    context = "\n\n---\n\n".join(
        f"[Page {m['page']}]\n{c}" for c, m in zip(chunks, metas)
    )
    history_block = f"{history_text}\n\n" if history_text else ""
    return (
        "You are a helpful assistant answering questions about a document.\n"
        "Answer using ONLY the context provided. Always cite the page number.\n"
        "If the answer is not in the context, say: \"I couldn't find that in the document.\"\n"
        "Use the conversation history to understand follow-up questions.\n\n"
        f"{history_block}"
        f"CONTEXT (retrieved for current question):\n{context}\n\n"
        f"CURRENT QUESTION: {question}\n\nANSWER:"
    )


def crag_query(question, history_text, embed_model, collection, claude_client):
    """
    CRAG pipeline: retrieve → grade → branch → generate.

    Paths:
      "direct"  — chunks are relevant, proceed to generation unchanged
      "rewrite" — chunks are partial, rewrite query and retrieve again
      "web"     — chunks are irrelevant, fall back to web search

    Returns:
      answer, chunks, metas, distances, grades, path, rewritten_q
      rewritten_q is the reformulated query string (rewrite path only), else None.
    """
    from query import retrieve, ask_claude

    # Step 1: retrieve
    chunks, metas, distances = retrieve(question, embed_model, collection)

    # Step 2: grade each chunk
    grades = grade_chunks(question, chunks, claude_client)
    overall = _best_grade(grades)

    # Step 3: branch
    rewritten_q = None

    if overall == "RELEVANT":
        path = "direct"
        use_chunks, use_metas = chunks, metas

    elif overall == "PARTIAL":
        path = "rewrite"
        rewritten_q = rewrite_query(question, claude_client)
        use_chunks, use_metas, distances = retrieve(rewritten_q, embed_model, collection)

    else:  # IRRELEVANT
        path = "web"
        web_ctx = web_search(question)
        if web_ctx.startswith("Web search unavailable"):
            # Web search failed — return a clear message without calling Claude.
            # Never pass a search error as WEB RESULTS — Claude will generate from
            # training data instead of stopping, producing ungrounded output.
            answer = (
                "This question isn't covered in the document and the web search is "
                "currently unavailable. Please try again or rephrase your question."
            )
            return answer, [], [], [], grades, path, None
        web_prompt = (
            "You are a helpful assistant. Answer the question using ONLY the web search results below.\n"
            "Do not use any prior knowledge. If the results don't contain an answer, say so clearly.\n\n"
            f"WEB RESULTS:\n{web_ctx}\n\n"
            f"QUESTION: {question}\n\nANSWER:"
        )
        answer = ask_claude(web_prompt, claude_client)
        return answer, [], [], [], grades, path, None

    # Step 4: generate (direct or rewrite path)
    prompt = _build_prompt(question, use_chunks, use_metas, history_text)
    answer = ask_claude(prompt, claude_client)
    return answer, use_chunks, use_metas, distances, grades, path, rewritten_q
