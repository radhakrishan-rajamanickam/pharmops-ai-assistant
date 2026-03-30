# =============================================================================
# rag_tool.py — RAG Retrieval Tool
# Architecture layer: RAG (document knowledge layer)
# This file is called by the agent when a question needs SOP document knowledge.
# It loads the FAISS index, searches for relevant chunks, and returns
# formatted results with source filenames for citation.
# =============================================================================

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

# Path to the saved FAISS index — built by ingest.py
FAISS_DIR = "data/faiss_index"

# How many chunks to retrieve per query
# 3 is enough context without overwhelming the LLM with too many tokens
TOP_K = 3

# Load the FAISS index once when this module is imported
# This avoids reloading from disk on every question — much faster
print("Loading FAISS index...")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
vectorstore = FAISS.load_local(
    FAISS_DIR,
    embeddings,
    allow_dangerous_deserialization=True
)
print("FAISS index loaded — RAG tool ready.")


def search_sop_documents(query: str) -> str:
    """
    Search the SOP knowledge base for chunks relevant to the query.

    Architecture role: This is the RAG tool exposed to the LangChain agent.
    The agent calls this function when it needs policy or procedure knowledge.

    How it works:
    1. Gemini converts the query string into a vector (embedding)
    2. FAISS finds the TOP_K chunks whose vectors are closest to the query vector
    3. Results are formatted as a string with source filename and content
    4. The agent receives this string as context to generate its answer

    Args:
        query: Natural language question from the user or agent

    Returns:
        Formatted string with retrieved SOP chunks and their source files
    """

    # Search the vector store — returns LangChain Document objects
    results = vectorstore.similarity_search(query, k=TOP_K)

    if not results:
        return "No relevant SOP documents found for this query."

    # Format results as a clean string the agent can read
    # Include source filename so the agent can cite it in the answer
    formatted = []
    for i, doc in enumerate(results):
        source = doc.metadata.get("source", "Unknown SOP")
        content = doc.page_content.strip()
        formatted.append(
            f"[Source {i+1}: {source}]\n{content}"
        )

    return "\n\n---\n\n".join(formatted)


# Test block — runs only when you execute: python src/rag_tool.py directly
if __name__ == "__main__":
    print("\n=== RAG Tool Test ===\n")

    # Test 1 — RAG only question
    q1 = "What is the procedure for handling a cold chain temperature deviation?"
    print(f"Question: {q1}")
    print("-" * 60)
    print(search_sop_documents(q1))

    print("\n" + "=" * 60 + "\n")

    # Test 2 — GxP question
    q2 = "What happens when a supplier GxP certificate expires?"
    print(f"Question: {q2}")
    print("-" * 60)
    print(search_sop_documents(q2))