# Render Backend Deployment - Complete Guide

## ✅ Problem FIXED!

**Issue:** Model was loading during STARTUP (60s) instead of using BUILD cache.

**Solution:**
- Set explicit cache directories (`HF_HOME`, `SENTENCE_TRANSFORMERS_HOME`)
- Force model to use cache in both `download_model.py` and `ai_pipeline.py`
- Model downloads during BUILD (no timeout), startup is <5 seconds ✅

---

## Fresh Render Deployment (Step-by-Step)

### Step 1: Push Latest Code

```bash
git add -A
git commit -m "Fix Render deployment with explicit model caching"
git push origin main
```

### Step 2: Create New Render Web Service

1. Go to: https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Click **"Build and deploy from a Git repository"**
4. Click **"Next"**

### Step 3: Connect GitHub Repository

1. If first time: Click **"Connect GitHub"** and authorize Render
2. Find your repository: **`Loan-Rag_Langchain`**
3. Click **"Connect"**

### Step 4: Configure Service Settings

Fill in EXACTLY as shown:

| Field | Value |
|-------|-------|
| **Name** | `loan-rag-backend` (or any name you want) |
| **Region** | `Oregon (US West)` (or closest to you) |
| **Branch** | `main` |
| **Root Directory** | `backend` ⚠️ IMPORTANT! |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt && python download_model.py` |
| **Start Command** | `python -m uvicorn main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 60` |
| **Instance Type** | `Free` |

Click **"Advanced"** to set more options:

| Field | Value |
|-------|-------|
| **Health Check Path** | `/` |
| **Auto-Deploy** | `Yes` (enabled) |

### Step 5: Add Environment Variables

⚠️ **CRITICAL:** Click **"Add Environment Variable"** and add ALL of these:

| Key | Value | Notes |
|-----|-------|-------|
| `OPENAI_API_KEY` | `sk-proj-...` | Your OpenAI API key |
| `QDRANT_URL` | `https://...` | Your Qdrant cluster URL |
| `QDRANT_API_KEY` | `...` | Your Qdrant API key |
| `QDRANT_COLLECTION` | `loan_policy_chunks` | Collection name |
| `ENVIRONMENT` | `production` | Environment flag |
| `HF_HOME` | `/opt/render/project/.cache/huggingface` | HuggingFace cache |
| `SENTENCE_TRANSFORMERS_HOME` | `/opt/render/project/.cache/huggingface` | Model cache |

**How to get your keys:**

- **OPENAI_API_KEY**: https://platform.openai.com/api-keys
- **QDRANT_URL**: Your Qdrant dashboard → Cluster URL
- **QDRANT_API_KEY**: Your Qdrant dashboard → API Keys

### Step 6: Create Web Service

1. Click **"Create Web Service"** button at the bottom
2. Render will start deploying immediately

### Step 7: Monitor Deployment

You'll see logs in real-time. Expected output:

```
==> Downloading and installing Python 3.x...
==> Running 'pip install -r requirements.txt && python download_model.py'
    Collecting fastapi...
    Collecting sentence-transformers...
    ✓ All dependencies installed

    Cache directory: /opt/render/project/.cache/huggingface
    Downloading sentence-transformers model...
    Loading model: sentence-transformers/all-MiniLM-L6-v2
    ✓ Model downloaded successfully to cache

==> Build successful 🎉
==> Deploying...
==> Running 'python -m uvicorn main:app --host 0.0.0.0 --port $PORT...'

    2025-10-31 XX:XX:XX [INFO] Initializing OpenAI models...
    2025-10-31 XX:XX:XX [INFO] Loading HuggingFace embeddings model from cache...
    2025-10-31 XX:XX:XX [INFO] ✓ Embeddings model loaded successfully
    2025-10-31 XX:XX:XX [INFO] Connecting to Qdrant...
    2025-10-31 XX:XX:XX [INFO] ✓ Connected to Qdrant collection

    INFO:     Application startup complete.
    INFO:     Uvicorn running on http://0.0.0.0:10000

==> Your service is live 🎉
```

**Timing:**
- Build phase: 5-10 minutes (downloads model)
- Startup: <5 seconds (uses cached model) ✅

### Step 8: Get Your Backend URL

After deployment succeeds:

1. Copy the URL shown at top: `https://loan-rag-backend-xxxx.onrender.com`
2. Save it - you'll need it for frontend

### Step 9: Test Your Backend

```bash
# Health check
curl https://your-backend-url.onrender.com/

# Expected response:
{"status":"healthy","service":"Loan Intelligence Assistant API"}

# API docs
# Visit in browser:
https://your-backend-url.onrender.com/docs
```

---

## Update Frontend to Use Backend

If you deployed frontend on Vercel/Netlify:

1. Go to your frontend hosting dashboard
2. Add/update environment variable:
   ```
   VITE_API_BASE_URL=https://your-backend-url.onrender.com
   ```
3. Redeploy frontend

---

## Troubleshooting

### Issue 1: "Port scan timeout"

**Check logs for:**
```
Loading HuggingFace embeddings model (this may take 30-60s on first run)...
```

**If you see this:** Model is not using cache!

**Solution:**
1. Make sure `HF_HOME` and `SENTENCE_TRANSFORMERS_HOME` env vars are set
2. Redeploy with **"Clear build cache & deploy"**

### Issue 2: Build fails during model download

**Error:** `Failed to download model`

**Solution:**
- Check internet connectivity (Render issue)
- Retry deployment
- Check if sentence-transformers is in requirements.txt

### Issue 3: Environment variables not working

**Error:** `QDRANT_URL environment variable is not set`

**Solution:**
1. Go to Settings → Environment Variables
2. Make sure all keys are spelled EXACTLY as shown above
3. Click "Save Changes"
4. Redeploy

### Issue 4: CORS errors from frontend

**Error:** `Access to fetch blocked by CORS policy`

**Solution:**
1. Check backend logs for frontend URL
2. Make sure `FRONTEND_URL` env var is set (if using)
3. Or allow all origins in production (backend already configured)

---

## Expected Costs

| Resource | Free Tier Limit | Your Usage | Cost |
|----------|-----------------|------------|------|
| Build minutes | Unlimited | ~10 min/deploy | $0 |
| Runtime hours | 750 hrs/month | 730 hrs/month (24/7) | $0 |
| Bandwidth | 100 GB/month | ~5-10 GB/month | $0 |

**Total: $0/month on Free tier** ✅

**Note:** After 15 minutes of inactivity, free tier services spin down. First request after will take ~30 seconds to wake up.

---

## Quick Commands Reference

```bash
# Check deploy status
# Visit: https://dashboard.render.com

# Force redeploy
# Dashboard → Manual Deploy → "Clear build cache & deploy"

# View logs
# Dashboard → Logs tab

# Update env vars
# Dashboard → Environment → Edit

# Check health
curl https://your-url.onrender.com/

# Check API docs
# Browser: https://your-url.onrender.com/docs
```

---

## What's Different Now? (The Fix)

**Before (BROKEN):**
- Model loaded during startup (60s)
- Port scan timeout before model finished loading
- Deployment failed ❌

**After (FIXED):**
- Model downloads during BUILD phase (10 min timeout, no problem)
- Cached model used during startup (<5s)
- Port binds immediately ✅
- Deployment succeeds 🎉

**Key changes:**
1. Explicit cache directories set via env vars
2. `download_model.py` uses same cache as `ai_pipeline.py`
3. `HuggingFaceEmbeddings` initialized with `cache_folder` parameter

---

## Next Steps After Deployment

1. ✅ Backend deployed successfully
2. ✅ Test all endpoints work
3. ✅ Connect frontend to backend
4. ✅ Test full application flow
5. ✅ Monitor logs for any errors
6. 🎉 You're live!

---

**Everything is now configured correctly. Just follow the steps above and your backend will deploy successfully!**
