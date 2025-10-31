# Vercel FastAPI Deployment Guide

## ⚠️ IMPORTANT WARNING

**Your app will likely NOT work on Vercel Free tier** due to:

1. **Size Limit**: Vercel Free = 50MB, your dependencies = ~500MB
   - sentence-transformers: ~100MB
   - torch (dependency): ~200MB+
   - Other ML libraries: ~200MB

2. **Cold Start**: 10-second timeout, your model loading takes 30-60s

3. **Serverless Architecture**: Each request = new instance = reload everything

## Recommended Solutions

### Option A: Keep Using Render (RECOMMENDED)
- Render supports long-running processes
- No size limits on Free tier
- Already configured and working
- Better for ML/AI applications

### Option B: Use Vercel with External Model Hosting
- Host embeddings model on separate service (HuggingFace Inference API)
- Keep only API logic on Vercel
- Requires code refactoring

### Option C: Upgrade Vercel to Pro
- Pro tier: 250MB limit (still might not be enough)
- Cost: $20/month per member

## If You Still Want to Try Vercel Free Tier

### Prerequisites
1. Vercel account (https://vercel.com)
2. Vercel CLI installed: `npm install -g vercel`
3. GitHub repository connected

### Step 1: Install Vercel CLI
```bash
npm install -g vercel
```

### Step 2: Login to Vercel
```bash
vercel login
```

### Step 3: Set Environment Variables
Go to Vercel Dashboard → Your Project → Settings → Environment Variables

Add these variables:
- `OPENAI_API_KEY` = (your OpenAI key)
- `QDRANT_URL` = (your Qdrant URL)
- `QDRANT_API_KEY` = (your Qdrant API key)
- `QDRANT_COLLECTION` = loan_policy_chunks
- `ENVIRONMENT` = production
- `FRONTEND_URL` = (your frontend URL)

### Step 4: Deploy

#### Option A: Deploy via GitHub (Recommended)
1. Push your code to GitHub
2. Go to https://vercel.com/new
3. Import your GitHub repository
4. Vercel will auto-detect `vercel.json` and deploy

#### Option B: Deploy via CLI
```bash
cd c:\Users\priya\Desktop\Loan_Final_rag
vercel --prod
```

### Step 5: Expected Issues & Solutions

#### Issue 1: "Deployment size exceeds limit"
**Solution**: Remove sentence-transformers and use OpenAI embeddings instead
```python
# In ai_pipeline.py, replace:
from langchain_huggingface import HuggingFaceEmbeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# With:
from langchain_openai import OpenAIEmbeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
```

#### Issue 2: "Function execution timeout"
**Solution**:
- Vercel Free: 10s max (can't be changed)
- Vercel Pro: 60s max
- Optimize cold starts or use Render instead

#### Issue 3: "Module import error"
**Solution**: Check vercel.json paths are correct

### Step 6: Test Deployment
Once deployed, test these endpoints:
- Health: `https://your-app.vercel.app/`
- Docs: `https://your-app.vercel.app/docs`
- Forms: `https://your-app.vercel.app/form-templates`

## Files Created for Vercel

✅ `vercel.json` - Vercel configuration
✅ `backend/vercel_app.py` - Serverless entry point
✅ `.gitignore` - Git ignore file
✅ `requirements.txt` - Python dependencies (at root)

## Comparison: Render vs Vercel

| Feature | Render | Vercel |
|---------|--------|--------|
| **Type** | Long-running server | Serverless functions |
| **Size Limit** | Unlimited (Free) | 50MB (Free) |
| **Timeout** | No limit | 10s (Free) |
| **Cold Start** | Once at deploy | Every request |
| **Best For** | ML/AI apps | Lightweight APIs |
| **Cost (Free)** | 750 hrs/month | Unlimited requests |
| **Verdict** | ✅ Better for your app | ❌ Won't work easily |

## My Recommendation

**Stick with Render.** Your app is better suited for a traditional server environment, not serverless.

If you need Vercel for frontend hosting, that's perfect! Host:
- **Backend on Render** (FastAPI + ML models)
- **Frontend on Vercel** (React/Vue/Next.js)

This gives you the best of both worlds.
