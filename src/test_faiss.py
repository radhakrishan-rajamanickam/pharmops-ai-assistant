from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

# Load the FAISS index we built in Step 7
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
db = FAISS.load_local(
    "data/faiss_index",
    embeddings,
    allow_dangerous_deserialization=True
)

# How many chunks are stored?
print(f"Total chunks stored in FAISS: {db.index.ntotal}")
print()

# Ask a question — find the 3 most relevant chunks
query = "cold chain temperature deviation"
results = db.similarity_search(query, k=3)

print(f"Top 3 chunks for query: '{query}'")
print("=" * 50)
for i, doc in enumerate(results):
    print(f"Chunk {i+1} — Source: {doc.metadata['source']}")
    print(doc.page_content[:200])
    print("-" * 50)
