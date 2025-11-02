"""
Automatically upload PDFs to Qdrant with intelligent domain classification
This script will:
1. Scan all PDFs and auto-detect their domain (residential/commercial/smsf/construction)
2. Split into 2000-token chunks
3. Add metadata tags to each chunk
4. Upload to Qdrant with OpenAI embeddings (1536 dimensions)
"""
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Configuration
PDFS_FOLDER = BASE_DIR.parent / "pdfs"
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "loan_policy_chunks")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

print("=" * 80)
print("🤖 AUTOMATED PDF UPLOAD WITH INTELLIGENT DOMAIN CLASSIFICATION")
print("=" * 80)

# Validate environment
if not OPENAI_API_KEY:
    print("❌ ERROR: OPENAI_API_KEY not found in .env file!")
    exit(1)

if not QDRANT_URL or not QDRANT_API_KEY:
    print("❌ ERROR: QDRANT_URL or QDRANT_API_KEY not found in .env file!")
    exit(1)

if not PDFS_FOLDER.exists():
    print(f"❌ ERROR: PDFs folder not found: {PDFS_FOLDER}")
    exit(1)

print(f"✓ PDFs folder: {PDFS_FOLDER}")
print(f"✓ Qdrant URL: {QDRANT_URL}")
print(f"✓ Collection: {QDRANT_COLLECTION}")


def detect_domain(pdf_path: Path, first_page_text: str) -> str:
    """
    Intelligently detect the domain of a PDF based on filename and content.

    Returns: "commercial", "smsf", "construction", or "residential"
    """
    filename_lower = pdf_path.name.lower()
    content_lower = first_page_text[:2000].lower()  # Check first 2000 chars

    # Check filename first (most reliable)
    if any(keyword in filename_lower for keyword in ["commercial", "business", "office", "retail", "industrial"]):
        return "commercial"

    if any(keyword in filename_lower for keyword in ["smsf", "super", "self managed", "fund"]):
        return "smsf"

    if any(keyword in filename_lower for keyword in ["construction", "building", "develop"]):
        return "construction"

    # Check content for commercial indicators
    commercial_indicators = [
        "commercial property", "commercial loan", "business lending",
        "office property", "retail property", "industrial property",
        "commercial real estate", "investment property", "commercial lvr"
    ]
    commercial_score = sum(1 for term in commercial_indicators if term in content_lower)

    # Check content for SMSF indicators
    smsf_indicators = [
        "smsf", "self managed super", "superannuation fund", "trustee",
        "limited recourse", "lrba", "fund member"
    ]
    smsf_score = sum(1 for term in smsf_indicators if term in content_lower)

    # Check content for construction indicators
    construction_indicators = [
        "construction loan", "building loan", "progress payment",
        "land and construct", "build", "development finance"
    ]
    construction_score = sum(1 for term in construction_indicators if term in content_lower)

    # Determine domain based on scores
    max_score = max(commercial_score, smsf_score, construction_score)

    if max_score > 0:
        if commercial_score == max_score:
            return "commercial"
        elif smsf_score == max_score:
            return "smsf"
        elif construction_score == max_score:
            return "construction"

    # Default to residential (most common)
    return "residential"


def load_and_classify_pdfs() -> List[Tuple[Path, str]]:
    """
    Load all PDFs and classify them by domain.
    Returns list of (pdf_path, domain) tuples.
    """
    pdf_files = list(PDFS_FOLDER.glob("*.pdf"))

    if not pdf_files:
        print(f"❌ ERROR: No PDF files found in {PDFS_FOLDER}")
        exit(1)

    print(f"\n📚 Found {len(pdf_files)} PDF files")
    print("=" * 80)

    classified = []

    for pdf_path in pdf_files:
        print(f"\n📄 Analyzing: {pdf_path.name}")

        try:
            # Load first page to analyze content
            loader = PyPDFLoader(str(pdf_path))
            pages = loader.load()

            if not pages:
                print(f"  ⚠️  Warning: Could not read PDF, defaulting to 'residential'")
                classified.append((pdf_path, "residential"))
                continue

            first_page_text = pages[0].page_content
            domain = detect_domain(pdf_path, first_page_text)

            classified.append((pdf_path, domain))
            print(f"  ✓ Classified as: {domain.upper()}")

        except Exception as e:
            print(f"  ❌ Error reading PDF: {e}")
            print(f"  ⚠️  Defaulting to 'residential'")
            classified.append((pdf_path, "residential"))

    return classified


def upload_pdfs_with_metadata(classified_pdfs: List[Tuple[Path, str]]):
    """
    Upload all PDFs to Qdrant with proper metadata tags.
    """
    print("\n" + "=" * 80)
    print("🚀 STEP 1: Initializing Qdrant and OpenAI")
    print("=" * 80)

    # Initialize embeddings (1536 dimensions for text-embedding-3-small)
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        chunk_size=1000
    )
    print("✓ OpenAI embeddings initialized (text-embedding-3-small, 1536 dimensions)")

    # Connect to Qdrant
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    print(f"✓ Connected to Qdrant")

    # Recreate collection to ensure clean state
    print(f"\n🔄 Recreating collection '{QDRANT_COLLECTION}'...")
    try:
        qdrant_client.delete_collection(collection_name=QDRANT_COLLECTION)
        print("  ✓ Deleted old collection")
    except Exception:
        print("  ℹ️  No existing collection to delete")

    # Create new collection with correct dimensions
    qdrant_client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )
    print(f"  ✓ Created new collection with 1536 dimensions")

    # Create payload index for domain filtering
    from qdrant_client.models import PayloadSchemaType
    qdrant_client.create_payload_index(
        collection_name=QDRANT_COLLECTION,
        field_name="metadata.domain",
        field_schema=PayloadSchemaType.KEYWORD
    )
    print(f"  ✓ Created payload index for metadata.domain (enables filtering)")

    # Initialize text splitter (2000 token chunks as per your existing config)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    print("✓ Text splitter initialized (2000 tokens, 200 overlap)")

    # Process each PDF
    print("\n" + "=" * 80)
    print("🚀 STEP 2: Processing and Uploading PDFs")
    print("=" * 80)

    total_chunks = 0
    domain_stats = {"residential": 0, "commercial": 0, "smsf": 0, "construction": 0}

    for idx, (pdf_path, domain) in enumerate(classified_pdfs, 1):
        print(f"\n[{idx}/{len(classified_pdfs)}] Processing: {pdf_path.name}")
        print(f"  Domain: {domain.upper()}")

        try:
            # Load PDF
            loader = PyPDFLoader(str(pdf_path))
            documents = loader.load()
            print(f"  ✓ Loaded {len(documents)} pages")

            # Split into chunks
            chunks = text_splitter.split_documents(documents)
            print(f"  ✓ Split into {len(chunks)} chunks")

            # Add metadata to each chunk
            for chunk in chunks:
                chunk.metadata["domain"] = domain
                chunk.metadata["source_file"] = pdf_path.name
                # Keep existing metadata (page numbers, etc.)

            # Upload to Qdrant
            vectorstore = QdrantVectorStore.from_documents(
                chunks,
                embeddings,
                url=QDRANT_URL,
                api_key=QDRANT_API_KEY,
                collection_name=QDRANT_COLLECTION,
                force_recreate=False  # Don't recreate, add to existing
            )

            print(f"  ✓ Uploaded {len(chunks)} chunks with '{domain}' metadata")
            total_chunks += len(chunks)
            domain_stats[domain] += len(chunks)

        except Exception as e:
            print(f"  ❌ Error processing {pdf_path.name}: {e}")
            continue

    # Print summary
    print("\n" + "=" * 80)
    print("✅ UPLOAD COMPLETE!")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"  Total PDFs processed: {len(classified_pdfs)}")
    print(f"  Total chunks uploaded: {total_chunks}")
    print(f"\n📋 Chunks by domain:")
    print(f"  🏠 Residential:   {domain_stats['residential']:4d} chunks")
    print(f"  🏢 Commercial:    {domain_stats['commercial']:4d} chunks")
    print(f"  💰 SMSF:          {domain_stats['smsf']:4d} chunks")
    print(f"  🏗️  Construction: {domain_stats['construction']:4d} chunks")
    print(f"\n✅ Your RAG system is now ready with domain filtering!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        # Step 1: Classify all PDFs
        classified_pdfs = load_and_classify_pdfs()

        # Show classification summary
        print("\n" + "=" * 80)
        print("📊 CLASSIFICATION SUMMARY")
        print("=" * 80)

        domain_counts = {"residential": 0, "commercial": 0, "smsf": 0, "construction": 0}
        for _, domain in classified_pdfs:
            domain_counts[domain] += 1

        print(f"\n🏠 Residential:   {domain_counts['residential']} PDFs")
        print(f"🏢 Commercial:    {domain_counts['commercial']} PDFs")
        print(f"💰 SMSF:          {domain_counts['smsf']} PDFs")
        print(f"🏗️  Construction: {domain_counts['construction']} PDFs")

        # Auto-proceed in non-interactive mode
        print("\n" + "=" * 80)
        print("✅ Auto-proceeding with upload...")

        # Step 2: Upload with metadata
        upload_pdfs_with_metadata(classified_pdfs)

    except KeyboardInterrupt:
        print("\n\n❌ Upload cancelled by user (Ctrl+C)")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
