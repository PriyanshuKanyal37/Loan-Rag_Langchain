# 🏦 Loan RAG with LangChain

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-Enabled-green)
![Status](https://img.shields.io/badge/Status-Active-success)

**An intelligent loan information retrieval system powered by RAG (Retrieval Augmented Generation) and LangChain** 🤖

</div>

---

## 📋 Table of Contents

- [✨ Introduction](#-introduction)
- [🚀 Features](#-features)
- [🛠️ Tech Stack](#️-tech-stack)
- [📁 Project Structure](#-project-structure)
- [⚙️ Installation](#️-installation)
- [💻 Usage](#-usage)
- [🌐 Deployment](#-deployment)
- [🔌 API Documentation](#-api-documentation)
- [📄 Form Schemas](#-form-schemas)
- [👨‍💻 Development](#-development)
- [🤝 Contributors](#-contributors)

---

## ✨ Introduction

Loan RAG with LangChain is an advanced question-answering system designed to provide accurate and contextual information about loans, lending policies, and financial products. By leveraging Retrieval Augmented Generation (RAG) architecture and LangChain framework, this system combines the power of large language models with domain-specific knowledge retrieval to deliver precise, up-to-date responses to loan-related queries.

### Why This Project?

- **Accurate Information**: Retrieves information from verified loan documentation
- **Context-Aware Responses**: Uses RAG to provide relevant, contextual answers
- **Scalable Architecture**: Built with modern frameworks for easy deployment
- **Developer-Friendly**: Clean code structure and comprehensive documentation

---

## 🚀 Features

- 🔍 **Intelligent Document Retrieval**: Efficiently searches through loan documentation
- 💬 **Natural Language Understanding**: Understands complex loan-related queries
- 🎯 **Context-Aware Responses**: Provides accurate answers based on retrieved context
- ⚡ **Fast Processing**: Optimized for quick response times
- 🔒 **Secure**: Handles sensitive financial information with care
- 📊 **Vector Database Integration**: Uses efficient vector storage for document embeddings
- 🔄 **Real-time Updates**: Can be updated with new loan information

---

## 🛠️ Tech Stack

### Core Technologies

- **Python 3.8+**: Primary programming language
- **LangChain**: Framework for LLM application development
- **OpenAI GPT**: Large language model for generation
- **Vector Database**: (Pinecone/Chroma/FAISS) for document embeddings
- **FastAPI/Flask**: API framework for deployment

### Libraries & Tools

```python
- langchain
- openai
- tiktoken
- chromadb / pinecone-client / faiss-cpu
- python-dotenv
- pydantic
- uvicorn
- fastapi
```

---

## 📁 Project Structure

```
Loan-Rag_Langchain/
├── data/                      # Loan documentation and knowledge base
│   ├── raw/                   # Raw documents
│   └── processed/             # Processed and chunked documents
├── src/
│   ├── embeddings/           # Embedding generation modules
│   ├── retrieval/            # Document retrieval logic
│   ├── generation/           # Response generation
│   ├── chains/               # LangChain chain definitions
│   └── utils/                # Helper functions
├── api/
│   ├── main.py               # API entry point
│   ├── routes/               # API routes
│   └── schemas/              # Request/response schemas
├── configs/
│   └── config.py             # Configuration settings
├── tests/                    # Unit and integration tests
├── notebooks/                # Jupyter notebooks for exploration
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
└── README.md                # This file
```

---

## ⚙️ Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- OpenAI API key (or other LLM provider)
- Vector database account (if using cloud service)

### Step-by-Step Setup

1. **Clone the repository**

```bash
git clone https://github.com/PriyanshuKanyal37/Loan-Rag_Langchain.git
cd Loan-Rag_Langchain
```

2. **Create virtual environment**

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

5. **Prepare the knowledge base**

```bash
python src/utils/prepare_documents.py
```

6. **Initialize vector database**

```bash
python src/embeddings/create_embeddings.py
```

---

## 💻 Usage

### Command Line Interface

```bash
python main.py --query "What are the eligibility criteria for a home loan?"
```

### Python Script

```python
from src.chains.qa_chain import LoanRAGChain

# Initialize the chain
rag_chain = LoanRAGChain()

# Ask a question
response = rag_chain.query("What documents are required for a personal loan?")
print(response['answer'])
print("Sources:", response['sources'])
```

### API Server

1. **Start the server**

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

2. **Make API requests**

```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the interest rate for car loans?"}'
```

---

## 🌐 Deployment

### Docker Deployment

```bash
# Build the image
docker build -t loan-rag-api .

# Run the container
docker run -p 8000:8000 --env-file .env loan-rag-api
```

### Cloud Deployment Options

- **AWS**: Deploy on EC2, ECS, or Lambda
- **Google Cloud**: Use Cloud Run or GKE
- **Azure**: Deploy on App Service or AKS
- **Heroku**: Quick deployment with Procfile

### Environment Variables

```env
OPENAI_API_KEY=your_openai_key
VECTOR_DB_URL=your_vector_db_url
VECTOR_DB_API_KEY=your_db_api_key
MODEL_NAME=any model
TEMPERATURE=0.7
MAX_TOKENS=500
```

---

## 🔌 API Documentation

### Endpoints

#### POST /api/query

Query the loan RAG system with a question.

**Request Body:**
```json
{
  "question": "What are the requirements for a business loan?",
  "max_results": 3,
  "include_sources": true
}
```

**Response:**
```json
{
  "answer": "To apply for a business loan, you typically need...",
  "sources": [
    {
      "document": "business_loan_guide.pdf",
      "page": 5,
      "relevance_score": 0.92
    }
  ],
  "confidence": 0.89,
  "timestamp": "2025-11-01T12:40:00Z"
}
```

#### GET /api/health

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "vector_db_status": "connected"
}
```

---

## 📄 Form Schemas

### Query Request Schema

```python
from pydantic import BaseModel, Field
from typing import Optional

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The loan-related question")
    max_results: Optional[int] = Field(3, ge=1, le=10, description="Maximum number of sources")
    include_sources: Optional[bool] = Field(True, description="Include source documents")
    temperature: Optional[float] = Field(0.7, ge=0, le=1, description="Model temperature")
```

### Query Response Schema

```python
class SourceDocument(BaseModel):
    document: str
    page: Optional[int]
    relevance_score: float
    content_snippet: Optional[str]

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
    confidence: float
    timestamp: str
    processing_time_ms: int
```

---

## 👨‍💻 Development

### Setting Up Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_retrieval.py
```

### Code Quality

```bash
# Format code
black src/ api/ tests/

# Check linting
flake8 src/ api/

# Type checking
mypy src/
```

### Adding New Documents

1. Place documents in `data/raw/`
2. Run document processing: `python src/utils/process_documents.py`
3. Update embeddings: `python src/embeddings/update_embeddings.py`
4. Test retrieval: `python tests/test_new_documents.py`

---

## 🤝 Contributors

<div align="center">

### Project Maintainer

**Priyanshu Kanyal**  
[@PriyanshuKanyal37](https://github.com/PriyanshuKanyal37)

</div>

### How to Contribute

We welcome contributions! Here's how you can help:

1. 🍴 Fork the repository
2. 🌟 Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. 💾 Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. 📤 Push to the branch (`git push origin feature/AmazingFeature`)
5. 🎉 Open a Pull Request

### Areas We Need Help With

- 📚 Adding more loan documentation
- 🧪 Writing additional tests
- 📝 Improving documentation
- 🐛 Bug fixes and optimizations
- 🌍 Multi-language support

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


<div align="center">

**If you find this project helpful, please consider giving it a ⭐!**

Made with ❤️ by [Priyanshu Kanyal](https://github.com/PriyanshuKanyal37)

</div>
