"""
Verification script to preview chunking quality before uploading to Qdrant.
Run this to see how your PDFs will be chunked with the new strategy.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
PDF_FOLDER = PROJECT_ROOT / "pdfs"

load_dotenv(BASE_DIR / ".env")


def preview_chunking(pdf_name: str = None, max_chunks: int = 5):
    """
    Preview how a PDF will be chunked with the new strategy.

    Args:
        pdf_name: Specific PDF filename (e.g., "Brighten Resident Lending Guidelines 03042024 - Final (1).pdf")
                  If None, uses the first PDF found
        max_chunks: Maximum number of chunks to display
    """
    pdf_files = sorted(p for p in PDF_FOLDER.glob("*.pdf"))

    if not pdf_files:
        print("❌ No PDF files found in the 'pdfs' folder.")
        return

    # Select PDF to preview
    if pdf_name:
        target_pdf = PDF_FOLDER / pdf_name
        if not target_pdf.exists():
            print(f"❌ PDF '{pdf_name}' not found.")
            print(f"Available PDFs:")
            for p in pdf_files:
                print(f"  - {p.name}")
            return
    else:
        target_pdf = pdf_files[0]

    print(f"\n{'='*80}")
    print(f"PREVIEWING CHUNKING FOR: {target_pdf.name}")
    print(f"{'='*80}\n")

    # Load PDF
    loader = PyPDFLoader(str(target_pdf))
    docs = loader.load()
    print(f"✅ Loaded {len(docs)} pages from PDF\n")

    # IMPROVED CHUNKING STRATEGY
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=400,
        separators=["\n\n\n", "\n\n", "\n", ". ", ", ", " ", ""],
        length_function=len,
        is_separator_regex=False,
    )

    chunks = text_splitter.split_documents(docs)
    print(f"✅ Created {len(chunks)} chunks (chunk_size=2000, overlap=400)\n")

    # Display statistics
    chunk_sizes = [len(c.page_content) for c in chunks]
    avg_size = sum(chunk_sizes) / len(chunk_sizes)
    min_size = min(chunk_sizes)
    max_size = max(chunk_sizes)

    print(f"📊 CHUNK STATISTICS:")
    print(f"   Average size: {avg_size:.0f} characters")
    print(f"   Min size: {min_size} characters")
    print(f"   Max size: {max_size} characters")
    print(f"\n{'='*80}\n")

    # Preview first N chunks
    for idx, chunk in enumerate(chunks[:max_chunks], 1):
        print(f"CHUNK {idx}/{len(chunks)}")
        print(f"Size: {len(chunk.page_content)} chars")
        print(f"Page: {chunk.metadata.get('page', 'N/A')}")
        print(f"Source: {Path(chunk.metadata.get('source', '')).name}")
        print(f"\n--- CONTENT PREVIEW ---")
        print(chunk.page_content[:800])  # First 800 chars
        if len(chunk.page_content) > 800:
            print(f"\n... ({len(chunk.page_content) - 800} more characters)")
        print(f"\n{'='*80}\n")

    if len(chunks) > max_chunks:
        print(f"... and {len(chunks) - max_chunks} more chunks (not shown)")

    # Analyze policy coverage
    print(f"\n{'='*80}")
    print(f"POLICY COVERAGE ANALYSIS:")
    print(f"{'='*80}\n")

    policy_terms = {
        "LVR": ["lvr", "loan-to-value", "loan to value"],
        "DTI": ["dti", "debt-to-income", "debt to income"],
        "Loan Amount": ["minimum loan", "maximum loan", "loan amount"],
        "Property Value": ["property value", "property price"],
        "Income/Employment": ["income", "employment", "payg", "self-employed"],
        "SMSF": ["smsf", "super", "self managed"],
        "Construction": ["construction", "builder", "progress payment"],
        "Commercial": ["commercial", "business", "industrial"],
    }

    for policy_type, terms in policy_terms.items():
        chunks_with_policy = sum(
            1 for chunk in chunks
            if any(term in chunk.page_content.lower() for term in terms)
        )
        percentage = (chunks_with_policy / len(chunks)) * 100 if chunks else 0
        print(f"{policy_type:20s}: {chunks_with_policy:3d} chunks ({percentage:5.1f}%)")

    print(f"\n{'='*80}\n")


def compare_chunking_strategies():
    """Compare old vs new chunking strategy side-by-side."""
    pdf_files = sorted(p for p in PDF_FOLDER.glob("*.pdf"))

    if not pdf_files:
        print("❌ No PDF files found.")
        return

    target_pdf = pdf_files[0]
    loader = PyPDFLoader(str(target_pdf))
    docs = loader.load()

    print(f"\n{'='*80}")
    print(f"COMPARING CHUNKING STRATEGIES: {target_pdf.name}")
    print(f"{'='*80}\n")

    # OLD STRATEGY
    old_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    old_chunks = old_splitter.split_documents(docs)

    # NEW STRATEGY
    new_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=400,
        separators=["\n\n\n", "\n\n", "\n", ". ", ", ", " ", ""],
    )
    new_chunks = new_splitter.split_documents(docs)

    print(f"📊 COMPARISON:")
    print(f"   OLD Strategy: {len(old_chunks)} chunks (size=1000, overlap=150)")
    print(f"   NEW Strategy: {len(new_chunks)} chunks (size=2000, overlap=400)")
    print(f"   Reduction: {len(old_chunks) - len(new_chunks)} chunks ({((len(old_chunks) - len(new_chunks)) / len(old_chunks) * 100):.1f}% fewer)")
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Preview specific PDF
        preview_chunking(pdf_name=sys.argv[1])
    else:
        # Show comparison and preview first PDF
        compare_chunking_strategies()
        print("\n")
        preview_chunking()
