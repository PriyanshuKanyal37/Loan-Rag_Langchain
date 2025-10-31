"""
Upload PDF documents to Qdrant vector database with OpenAI embeddings
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Configuration
PDFS_FOLDER = BASE_DIR.parent / "pdfs"
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "loan_policy_chunks")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

print("="*70)
print("PDF Upload to Qdrant - OpenAI Embeddings (1536 dimensions)")
print("="*70)

# Validate environment
if not OPENAI_API_KEY:
    print("[ERROR] OPENAI_API_KEY not found in .env file!")
    exit(1)

if not QDRANT_URL or not QDRANT_API_KEY:
    print("[ERROR] QDRANT_URL or QDRANT_API_KEY not found in .env file!")
    exit(1)

if not PDFS_FOLDER.exists():
    print(f"[ERROR] PDFs folder not found: {PDFS_FOLDER}")
    exit(1)

print(f"\nPDFs folder: {PDFS_FOLDER}")
print(f"Qdrant URL: {QDRANT_URL}")
print(f"Collection: {QDRANT_COLLECTION}")

# Find all PDF files
pdf_files = list(PDFS_FOLDER.glob("*.pdf"))
print(f"\nFound {len(pdf_files)} PDF files:")
for pdf in pdf_files:
    print(f"  - {pdf.name}")

if not pdf_files:
    print("\n[ERROR] No PDF files found in pdfs/ folder!")
    exit(1)

# Initialize OpenAI embeddings
print("\nInitializing OpenAI embeddings...")
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",  # 1536 dimensions
    chunk_size=1000
)
print("[OK] OpenAI embeddings initialized (1536 dimensions)")

# Initialize text splitter
# Increased chunk size to 2000 for better context retention
print("\nInitializing text splitter...")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=400,
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""]
)
print("[OK] Text splitter initialized (chunk_size=2000, overlap=400)")

# Load and process all PDFs
print("\nLoading and processing PDFs...")
all_documents = []

for pdf_path in pdf_files:
    try:
        print(f"\n  Processing: {pdf_path.name}")

        # Load PDF
        loader = PyPDFLoader(str(pdf_path))
        documents = loader.load()
        print(f"    Loaded {len(documents)} pages")

        # Split into chunks
        chunks = text_splitter.split_documents(documents)
        print(f"    Split into {len(chunks)} chunks")

        # Add source metadata
        for chunk in chunks:
            chunk.metadata["source"] = pdf_path.name
            chunk.metadata["file_path"] = str(pdf_path)

        all_documents.extend(chunks)
        print(f"    [OK] Added {len(chunks)} chunks to upload queue")

    except Exception as e:
        print(f"    [ERROR] processing {pdf_path.name}: {e}")
        continue

print(f"\n[OK] Total chunks ready for upload: {len(all_documents)}")

if not all_documents:
    print("\n[ERROR] No documents to upload!")
    exit(1)

# Connect to Qdrant
print(f"\nConnecting to Qdrant...")
qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
print("[OK] Connected to Qdrant")

# Check if we should force recreate
force_recreate = os.environ.get("QDRANT_FORCE_RECREATE", "false").lower() == "true"

if force_recreate:
    print(f"\n[WARNING] QDRANT_FORCE_RECREATE=true detected")
    print(f"  This will DELETE and RECREATE the collection: {QDRANT_COLLECTION}")
    print(f"  Auto-confirming (running non-interactively)...")

# Upload to Qdrant
print(f"\nUploading {len(all_documents)} chunks to Qdrant...")
print(f"  Collection: {QDRANT_COLLECTION}")
print(f"  Force recreate: {force_recreate}")
print(f"\n  This may take a few minutes (calling OpenAI API for embeddings)...")

try:
    vectorstore = QdrantVectorStore.from_documents(
        all_documents,
        embeddings,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=QDRANT_COLLECTION,
        force_recreate=force_recreate,
    )

    print(f"\n[SUCCESS] Uploaded {len(all_documents)} chunks to Qdrant!")
    print(f"  Collection: {QDRANT_COLLECTION}")
    print(f"  Dimensions: 1536 (OpenAI text-embedding-3-small)")

except Exception as e:
    print(f"\n[ERROR] uploading to Qdrant: {e}")
    print(f"\nTroubleshooting:")
    print(f"  1. Check your Qdrant credentials in .env")
    print(f"  2. If dimension mismatch, set QDRANT_FORCE_RECREATE=true in .env")
    print(f"  3. Verify OpenAI API key has sufficient quota")
    exit(1)

# Verify upload
print(f"\nVerifying upload...")
try:
    collection_info = qdrant_client.get_collection(QDRANT_COLLECTION)
    print(f"[OK] Collection verified:")
    print(f"  Points count: {collection_info.points_count}")
    print(f"  Vector size: {collection_info.config.params.vectors.size}")

except Exception as e:
    print(f"[WARNING] Could not verify collection: {e}")

print("\n" + "="*70)
print("UPLOAD COMPLETE!")
print("="*70)
print(f"\nNext steps:")
print(f"  1. Remove QDRANT_FORCE_RECREATE=true from .env (if set)")
print(f"  2. Start your backend: cd backend && uvicorn main:app --reload")
print(f"  3. Test your API at: http://localhost:8000")
print("="*70)
