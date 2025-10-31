"""
Pre-download the embeddings model during build phase.
This prevents cold start timeout issues.
"""
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_embeddings_model():
    """Download HuggingFace embeddings model"""
    try:
        logger.info("Downloading sentence-transformers model...")
        from sentence_transformers import SentenceTransformer

        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        logger.info(f"Loading model: {model_name}")

        model = SentenceTransformer(model_name)
        logger.info(f"✓ Model downloaded successfully to cache")
        logger.info(f"  Model size: ~80MB")
        logger.info(f"  This will speed up application startup")

        return True
    except Exception as e:
        logger.error(f"❌ Failed to download model: {e}")
        return False

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("Pre-downloading embeddings model for faster startup")
    logger.info("="*60)

    success = download_embeddings_model()

    if success:
        logger.info("="*60)
        logger.info("✓ Model download complete!")
        logger.info("="*60)
        exit(0)
    else:
        logger.error("="*60)
        logger.error("❌ Model download failed!")
        logger.error("="*60)
        exit(1)
