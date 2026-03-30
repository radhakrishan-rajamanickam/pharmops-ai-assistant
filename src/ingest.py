# =============================================================================
# ingest.py — RAG Document Ingestion Pipeline
# Architecture layer: RAG (document knowledge layer)
# Run this file ONCE to build the FAISS vector index from SOP documents.
# After running, the index is saved to data/faiss_index/ and loaded by the app.
# =============================================================================

import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

# Load environment variables from .env file
# This gives us access to GOOGLE_API_KEY without hardcoding it in the code
load_dotenv()

# Path to the folder containing SOP text files
DOCS_DIR = "docs"

# Path where the FAISS index will be saved after ingestion
FAISS_DIR = "data/faiss_index"


def load_documents():
    """
    Step 1 — Load all .txt SOP files from the docs/ folder.
    Each file becomes a Document object with its content and filename as metadata.
    The filename is stored so we can show the user which SOP the answer came from.
    """
    docs = []
    for filename in os.listdir(DOCS_DIR):
        if filename.endswith(".txt"):
            path = os.path.join(DOCS_DIR, filename)

            # TextLoader reads the file and creates a Document object
            loader = TextLoader(path, encoding="utf-8")
            loaded = loader.load()

            # Tag each document with its source filename
            # This metadata travels with every chunk — used later for citations
            for doc in loaded:
                doc.metadata["source"] = filename

            docs.extend(loaded)
            print(f"  Loaded: {filename}")

    return docs


def chunk_documents(docs):
    """
    Step 2 — Split each document into smaller overlapping chunks.
    Why chunk? LLMs have a context window limit — we cannot feed 5 entire
    SOPs at once. Chunking lets us retrieve only the relevant pieces.
    chunk_size=500: each chunk is ~500 characters
    chunk_overlap=50: chunks overlap by 50 chars so context is not lost
    at boundaries between chunks.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "]
    )
    chunks = splitter.split_documents(docs)
    print(f"  Total chunks created: {len(chunks)}")
    return chunks


def build_index(chunks):
    """
    Step 3 — Convert each chunk into a vector embedding and store in FAISS.
    Embedding: a list of numbers (vector) that captures the semantic meaning
    of a piece of text. Similar meaning = similar vectors = close in space.
    FAISS (Facebook AI Similarity Search) is a library that stores these
    vectors and can find the most similar ones to a query very quickly.
    """
    print("  Creating embeddings — calling Gemini API, may take 30 seconds...")

    # Use Google Gemini's embedding model to convert text to vectors
    # gemini-embedding-001 is the confirmed working model for free tier
    # Discovered via: client.models.list() — see troubleshooting in README
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001"
    )

    # Build the FAISS index from all chunks and their embeddings
    # This is the core operation — each chunk becomes a searchable vector
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # Save the index to disk so we don't have to rebuild it every time
    # Creates two files: index.faiss (vectors) and index.pkl (metadata)
    vectorstore.save_local(FAISS_DIR)
    print(f"  FAISS index saved to: {FAISS_DIR}")


# Entry point — runs when you execute: python src/ingest.py
if __name__ == "__main__":
    print("=== PharmOps RAG Ingestion Pipeline ===\n")

    print("[1/3] Loading SOP documents from docs/ folder...")
    docs = load_documents()
    print(f"  Documents loaded: {len(docs)}\n")

    print("[2/3] Splitting documents into chunks...")
    chunks = chunk_documents(docs)
    print()

    print("[3/3] Building FAISS vector index...")
    build_index(chunks)

    print("\n=== Ingestion complete. FAISS index is ready. ===")

