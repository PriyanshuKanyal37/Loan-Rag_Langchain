"""
Script to add 'domain' metadata to all existing documents in Qdrant collection.

This script:
1. Fetches all documents from the Qdrant collection
2. Analyzes document content to determine domain (residential/commercial/smsf/construction)
3. Updates each document's metadata with the correct domain
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import re

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Load Qdrant configuration
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "loan_policy_chunks")

print("=" * 70)
print("QDRANT METADATA FIX - ADD DOMAIN TO ALL DOCUMENTS")
print("=" * 70)
print(f"Collection: {QDRANT_COLLECTION}")
print()

# Connect to Qdrant
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

def determine_domain(content: str, source: str = "") -> str:
    """
    Determine document domain based on content keywords.

    Args:
        content: Document text content
        source: Source file name (if available)

    Returns:
        Domain: "residential", "commercial", "smsf", or "construction"
    """
    content_lower = content.lower()
    source_lower = source.lower() if source else ""

    # Check source filename first (most reliable)
    if any(keyword in source_lower for keyword in ["smsf", "self managed", "super fund", "lrba"]):
        return "smsf"
    if any(keyword in source_lower for keyword in ["commercial", "business loan", "industrial", "retail"]):
        return "commercial"
    if any(keyword in source_lower for keyword in ["construction", "building", "builder"]):
        return "construction"
    if any(keyword in source_lower for keyword in ["residential", "home loan", "mortgage"]):
        return "residential"

    # Check content keywords
    smsf_keywords = [
        "smsf", "self managed super", "self-managed super", "lrba",
        "bare trust", "limited recourse", "super fund", "trustee",
        "superannuation fund", "complying fund"
    ]
    commercial_keywords = [
        "commercial property", "business loan", "commercial lending",
        "industrial property", "retail property", "warehouse",
        "business purpose", "commercial borrower", "business entity",
        "commercial security", "gst", "business revenue"
    ]
    construction_keywords = [
        "construction loan", "building contract", "builder",
        "construction stage", "progress payment", "fixed price contract",
        "owner builder", "construction phase", "building work",
        "slab stage", "frame stage", "completion stage"
    ]
    residential_keywords = [
        "residential property", "home loan", "owner occupied",
        "investment property", "principal and interest", "mortgage",
        "first home buyer", "lvr", "serviceability", "principal residence"
    ]

    # Count keyword matches
    smsf_score = sum(1 for kw in smsf_keywords if kw in content_lower)
    commercial_score = sum(1 for kw in commercial_keywords if kw in content_lower)
    construction_score = sum(1 for kw in construction_keywords if kw in content_lower)
    residential_score = sum(1 for kw in residential_keywords if kw in content_lower)

    # Return domain with highest score
    scores = {
        "smsf": smsf_score,
        "commercial": commercial_score,
        "construction": construction_score,
        "residential": residential_score,
    }

    max_domain = max(scores, key=scores.get)

    # If all scores are 0, default to residential (most common)
    if scores[max_domain] == 0:
        return "residential"

    return max_domain


def update_metadata():
    """Update metadata for all documents in the collection."""

    # Get collection info
    collection_info = client.get_collection(collection_name=QDRANT_COLLECTION)
    total_points = collection_info.points_count
    print(f"Total documents in collection: {total_points}")
    print()

    if total_points == 0:
        print("Collection is empty. Nothing to update.")
        return

    # Fetch all documents in batches
    print("Fetching all documents...")
    batch_size = 100
    offset = None
    all_points = []

    while True:
        batch, offset = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=True  # We need vectors to re-upload
        )

        if not batch:
            break

        all_points.extend(batch)
        print(f"  Fetched {len(all_points)}/{total_points} documents...", end="\r")

        if offset is None:
            break

    print(f"\n✓ Fetched {len(all_points)} documents")
    print()

    # Analyze and update metadata
    print("Analyzing documents and updating metadata...")
    domain_counts = {"residential": 0, "commercial": 0, "smsf": 0, "construction": 0}
    updated_points = []

    for idx, point in enumerate(all_points, 1):
        payload = point.payload or {}

        # Get content and source
        content = payload.get("page_content", "")
        metadata = payload.get("metadata", {})
        source = metadata.get("source", "") if isinstance(metadata, dict) else ""

        # Determine domain
        domain = determine_domain(content, source)
        domain_counts[domain] += 1

        # Update metadata with domain
        if isinstance(metadata, dict):
            metadata["domain"] = domain
        else:
            metadata = {"domain": domain}

        # Create updated payload
        updated_payload = {
            "page_content": content,
            "metadata": metadata
        }

        # Create updated point
        updated_point = PointStruct(
            id=point.id,
            vector=point.vector,
            payload=updated_payload
        )
        updated_points.append(updated_point)

        if idx % 100 == 0 or idx == len(all_points):
            print(f"  Processed {idx}/{len(all_points)} documents...", end="\r")

    print()
    print(f"✓ Analyzed {len(all_points)} documents")
    print()

    print("Domain distribution:")
    for domain, count in sorted(domain_counts.items()):
        percentage = (count / len(all_points)) * 100
        print(f"  {domain:15s}: {count:4d} documents ({percentage:5.1f}%)")
    print()

    # Upload updated documents
    print("Uploading updated documents to Qdrant...")
    upload_batch_size = 50
    for i in range(0, len(updated_points), upload_batch_size):
        batch = updated_points[i:i+upload_batch_size]
        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=batch
        )
        print(f"  Uploaded {min(i+upload_batch_size, len(updated_points))}/{len(updated_points)} documents...", end="\r")

    print()
    print(f"✓ Successfully updated {len(updated_points)} documents")
    print()

    # Verify the update
    print("Verifying metadata update...")
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    for domain in ["residential", "commercial", "smsf", "construction"]:
        count = client.count(
            collection_name=QDRANT_COLLECTION,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="domain",
                        match=MatchValue(value=domain)
                    )
                ]
            )
        )
        print(f"  Domain '{domain}': {count.count} documents")

    print()
    print("=" * 70)
    print("✅ METADATA UPDATE COMPLETE!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Re-enable domain filtering in main.py (uncomment the domain filter code)")
    print("2. Restart your backend server")
    print("3. Test your API again")


if __name__ == "__main__":
    try:
        update_metadata()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
