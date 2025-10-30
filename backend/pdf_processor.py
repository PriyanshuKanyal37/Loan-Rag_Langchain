import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
PDF_FOLDER = PROJECT_ROOT / "pdfs"

load_dotenv(BASE_DIR / ".env")


def get_qdrant_client() -> QdrantClient:
    url = os.environ.get("QDRANT_URL")
    api_key = os.environ.get("QDRANT_API_KEY")
    if not url:
        raise RuntimeError("QDRANT_URL environment variable is not set.")
    return QdrantClient(url=url, api_key=api_key)


def ensure_collection(client: QdrantClient, collection_name: str, vector_dim: int) -> None:
    if client.collection_exists(collection_name=collection_name):
        client.delete_collection(collection_name=collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=qdrant_models.VectorParams(size=vector_dim, distance=qdrant_models.Distance.COSINE),
    )


def enrich_chunks_with_context(chunks: List[Document]) -> List[Document]:
    """
    Enrich chunks with contextual metadata to improve retrieval.
    Adds document name, page info, and attempts to identify policy type.
    """
    enriched = []

    for chunk in chunks:
        # Extract lender name from filename
        source = chunk.metadata.get("source", "")
        filename = Path(source).stem if source else "Unknown"

        # Identify if this chunk contains key policy information
        content_lower = chunk.page_content.lower()

        # Tag chunks with policy categories for better retrieval
        tags = []
        if any(term in content_lower for term in ["lvr", "loan-to-value", "loan to value"]):
            tags.append("LVR_policy")
        if any(term in content_lower for term in ["dti", "debt-to-income", "debt to income"]):
            tags.append("DTI_policy")
        if any(term in content_lower for term in ["minimum loan", "maximum loan", "loan amount"]):
            tags.append("loan_amount_policy")
        if any(term in content_lower for term in ["property value", "property price", "valuation"]):
            tags.append("property_value_policy")
        if any(term in content_lower for term in ["income", "employment", "payg", "self-employed"]):
            tags.append("income_policy")
        if any(term in content_lower for term in ["smsf", "super", "self managed"]):
            tags.append("SMSF_policy")
        if any(term in content_lower for term in ["construction", "builder", "progress payment"]):
            tags.append("construction_policy")
        if any(term in content_lower for term in ["commercial", "business", "industrial"]):
            tags.append("commercial_policy")

        # Enrich metadata
        chunk.metadata["lender"] = filename
        chunk.metadata["policy_tags"] = tags
        chunk.metadata["char_count"] = len(chunk.page_content)

        enriched.append(chunk)

    return enriched


def process_pdfs():
    """Load PDFs, embed them, and push the vectors into Qdrant."""
    pdf_files = sorted(p for p in PDF_FOLDER.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found in the 'pdfs' folder.")
        return

    all_docs = []
    print(f"Found {len(pdf_files)} PDFs. Processing...")

    for path in pdf_files:
        loader = PyPDFLoader(str(path))
        docs = loader.load()
        all_docs.extend(docs)
        print(f"Loaded: {path.name}")

    # IMPROVED CHUNKING STRATEGY for Australian lending policy documents
    # Larger chunks preserve complete policy rules, tables, and multi-step criteria
    # Larger overlap ensures critical context isn't lost at boundaries
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,           # Increased from 1000 to capture complete policy sections
        chunk_overlap=400,         # Increased from 150 to preserve context across boundaries
        separators=[
            "\n\n\n",              # Priority 1: Multiple blank lines (section breaks)
            "\n\n",                # Priority 2: Paragraph breaks
            "\n",                  # Priority 3: Line breaks
            ". ",                  # Priority 4: Sentence breaks
            ", ",                  # Priority 5: Clause breaks
            " ",                   # Priority 6: Word breaks
            ""                     # Priority 7: Character breaks (last resort)
        ],
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_documents(all_docs)
    print(f"Created {len(chunks)} text chunks for embedding (chunk_size=2000, overlap=400)")

    # Enrich chunks with metadata tags for better retrieval
    enriched_chunks = enrich_chunks_with_context(chunks)
    print(f"Enriched {len(enriched_chunks)} chunks with policy tags and metadata")

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_dim = len(embeddings.embed_query("dimension probe"))

    client = get_qdrant_client()
    collection_name = os.environ.get("QDRANT_COLLECTION", "loan_policy_chunks")

    ensure_collection(client, collection_name, vector_dim)

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )
    vector_store.add_documents(enriched_chunks)

    print(f"Vector collection '{collection_name}' updated at {os.environ.get('QDRANT_URL')}")


if __name__ == "__main__":
    process_pdfs()
