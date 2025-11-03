"""
Diagnostic script to check Qdrant collection status and debug retrieval issues.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Load Qdrant configuration
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "loan_policy_chunks")

print("=" * 60)
print("QDRANT COLLECTION DIAGNOSTIC")
print("=" * 60)
print(f"Qdrant URL: {QDRANT_URL}")
print(f"Collection: {QDRANT_COLLECTION}")
print()

# Connect to Qdrant
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# Check collection info
try:
    collection_info = client.get_collection(collection_name=QDRANT_COLLECTION)
    print("✅ Collection exists")
    print(f"   Points count: {collection_info.points_count}")
    print(f"   Vectors config: {collection_info.config.params.vectors}")
    print()

    if collection_info.points_count == 0:
        print("🔴 PROBLEM: Collection is EMPTY!")
        print("   You need to upload PDF documents to the collection.")
        print("   Run: python upload_pdfs.py")
        print()
    else:
        print(f"✅ Collection has {collection_info.points_count} documents")
        print()

        # Sample a few documents to check metadata
        print("Sampling documents to check metadata...")
        sample_points = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=5,
            with_payload=True,
            with_vectors=False
        )

        if sample_points and sample_points[0]:
            print(f"Found {len(sample_points[0])} sample documents")
            print()

            for idx, point in enumerate(sample_points[0][:3], 1):
                print(f"Document {idx}:")
                print(f"   ID: {point.id}")
                payload = point.payload or {}
                print(f"   Metadata keys: {list(payload.keys())}")

                # Check domain field
                domain = payload.get("domain", "NOT SET")
                print(f"   Domain: {domain}")

                # Check source
                source = payload.get("source", "NOT SET")
                print(f"   Source: {source}")

                # Preview content
                page_content = payload.get("page_content", "")
                if page_content:
                    preview = page_content[:200] + "..." if len(page_content) > 200 else page_content
                    print(f"   Content preview: {preview}")
                print()

        # Test domain filtering
        print("Testing domain filters...")
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
            print(f"   Domain '{domain}': {count.count} documents")
        print()

        # Test a simple search
        print("Testing vector search...")
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        vectorstore = QdrantVectorStore(
            client=client,
            collection_name=QDRANT_COLLECTION,
            embedding=embeddings,
        )

        test_query = "minimum loan amount requirements purchase_application"
        print(f"Query: '{test_query}'")

        # Search without filter
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(test_query)
        print(f"   Without filter: {len(docs)} documents found")

        # Search with residential filter
        search_kwargs = {
            "k": 3,
            "filter": Filter(
                must=[
                    FieldCondition(
                        key="domain",
                        match=MatchValue(value="residential")
                    )
                ]
            )
        }
        retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)
        docs = retriever.invoke(test_query)
        print(f"   With 'residential' filter: {len(docs)} documents found")

        if docs:
            print()
            print("Sample document content:")
            print(f"   {docs[0].page_content[:300]}...")
        else:
            print()
            print("🔴 PROBLEM: No documents found with search!")
            print("   This means your embeddings or filters are not working.")

except Exception as e:
    print(f"❌ Error: {e}")
    print()
    print("Possible issues:")
    print("1. Collection doesn't exist - run upload_pdfs.py to create it")
    print("2. Wrong collection name in .env file")
    print("3. Invalid Qdrant credentials")

print()
print("=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
