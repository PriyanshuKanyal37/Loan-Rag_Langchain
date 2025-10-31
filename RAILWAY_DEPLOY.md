# Railway Deployment Guide

## Errors Fixed! ✅

### Backend Error:
```
NameError: name 'sentence' is not defined
```
**Solution:** Created `backend/download_model.py` script instead of inline Python command.

### Frontend Error:
```
sh: 1: npm: not found
```
**Solution:** Railway needs separate services for backend and frontend (can't mix Python + Node.js in one service).

---

## Important: Railway Architecture

**Railway requires SEPARATE services for backend and frontend!**

### Why?

Railway detects project type based on root files:
- Finds `requirements.txt` → Treats as Python project
- Finds `package.json` → Treats as Node.js project

**You cannot mix Python + Node.js in one Railway service!**

### Solution: Deploy as Two Services

1. **Backend Service**:
   - Uses `backend/railway.json`
   - Only installs Python dependencies
   - No heavy frontend dependencies

2. **Frontend Service**:
   - Uses `frontend/railway.json`
   - Only installs Node.js dependencies (small, ~50MB)
   - No heavy ML dependencies (500MB)

This is MUCH more efficient than trying to install both in one service!

---

## Prerequisites

1. Railway account: https://railway.app
2. GitHub repository connected
3. Credit card (required even for free tier)

---

## Deploy to Railway (Two Separate Services)

### Service 1: Deploy Backend

#### Step 1: Create Backend Service
1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your repository: `Loan-Rag_Langchain`
4. Click "Deploy Now"

#### Step 2: Configure Root Directory
1. Click on your service
2. Go to "Settings" tab
3. **IMPORTANT**: Set **Root Directory**: `backend`
4. Railway will now use `backend/railway.json` config
5. Click "Save"

#### Step 3: Add Environment Variables
Go to "Variables" tab and add:

```env
OPENAI_API_KEY=your_openai_key_here
QDRANT_URL=your_qdrant_url_here
QDRANT_API_KEY=your_qdrant_api_key_here
QDRANT_COLLECTION=loan_policy_chunks
ENVIRONMENT=production
```

#### Step 4: Deploy Backend
Railway will automatically:
- Install Python dependencies from `backend/requirements.txt`
- Run `python download_model.py` to cache embeddings
- Start uvicorn server
- Takes ~5 minutes (model download is slow)

**Note your backend URL**: `https://your-backend.railway.app`

---

### Service 2: Deploy Frontend

#### Step 1: Add New Service
1. In the same Railway project, click "+ New"
2. Select "GitHub Repo"
3. Choose the SAME repository: `Loan-Rag_Langchain`

#### Step 2: Configure Root Directory
1. Click on the new service
2. Go to "Settings" tab
3. **IMPORTANT**: Set **Root Directory**: `frontend`
4. Railway will now use `frontend/railway.json` config
5. Click "Save"

#### Step 3: Add Environment Variable
Go to "Variables" tab and add:

```env
VITE_API_BASE_URL=https://your-backend.railway.app
```

**Replace with your actual backend URL from Service 1!**

#### Step 4: Deploy Frontend
Railway will automatically:
- Install Node.js dependencies from `frontend/package.json` (~50MB)
- Run `npm run build`
- Start Vite preview server
- Takes ~2 minutes

---

### Step 5: Update Backend CORS

After both services are deployed, update backend CORS to allow frontend:

1. Go to backend service settings
2. Add environment variable:
```env
FRONTEND_URL=https://your-frontend.railway.app
```

3. Redeploy backend

---

### Method 2: Railway CLI

#### Step 1: Install Railway CLI
```bash
npm install -g @railway/cli
```

#### Step 2: Login
```bash
railway login
```

#### Step 3: Initialize Project
```bash
cd c:\Users\priya\Desktop\Loan_Final_rag
railway init
```

#### Step 4: Link to Project
```bash
railway link
```

#### Step 5: Set Environment Variables
```bash
railway variables set OPENAI_API_KEY=your_key_here
railway variables set QDRANT_URL=your_url_here
railway variables set QDRANT_API_KEY=your_key_here
railway variables set QDRANT_COLLECTION=loan_policy_chunks
railway variables set ENVIRONMENT=production
```

#### Step 6: Deploy
```bash
railway up
```

---

## Configuration Files

### railway.json (Created)
Railway will automatically detect this file and use it for deployment settings.

### Key Changes Made:
1. ✅ Created `backend/download_model.py` - Separate script to download embeddings
2. ✅ Updated `render.yaml` - Uses new script instead of inline command
3. ✅ Created `railway.json` - Railway-specific configuration

---

## Expected Build Output

When deploying, you should see:

```
✓ Installing dependencies from requirements.txt...
✓ Downloading sentence-transformers model...
  - Loading model: sentence-transformers/all-MiniLM-L6-v2
  - Model size: ~80MB
  - Model cached for faster startup
✓ Model download complete!
✓ Build successful
✓ Starting application...
✓ Application running on port 8000
```

---

## Troubleshooting

### Issue 1: Build still fails with quote error
**Solution**: Make sure you're using the latest code with `download_model.py` script

```bash
git pull origin main
railway up
```

### Issue 2: Port binding timeout
**Solution**: Railway requires PORT environment variable
- Railway automatically provides $PORT
- No manual configuration needed

### Issue 3: Model download timeout during startup
**Solution**: Model is now downloaded during BUILD phase, not startup
- Build phase has 30-minute timeout (plenty of time)
- Startup should be fast (<10 seconds)

### Issue 4: Import errors
**Solution**: Make sure Root Directory is set to `backend`
```bash
railway run printenv | grep ROOT
```

---

## Railway vs Render Comparison

| Feature | Railway | Render |
|---------|---------|--------|
| **Free Tier** | ❌ No (was removed) | ✅ 750 hrs/month |
| **Pricing** | $5 free credit/month | Free tier available |
| **Build Speed** | ⚡ Faster | Slower |
| **Deployment** | Easier | Easy |
| **Credit Card** | ✅ Required | ❌ Not required |
| **Monthly Cost** | ~$10-15 | $0 (free tier) |

---

## Cost Estimate (Railway)

Based on your app requirements:

```
Memory: ~512MB
CPU: ~0.5 vCPU
Runtime: 24/7

Estimated cost:
- RAM: 512MB × 730 hours × $0.000231/GB-hr = ~$0.08
- CPU: 0.5 vCPU × 730 hours × $0.000463/vCPU-hr = ~$0.17
- Total: ~$0.25/month

However, Railway typically bills ~$10-15/month for production apps.
```

---

## Recommendation

**If you're paying anyway, Railway is great!**

But if you want free hosting:
- ✅ **Render** - Free tier, perfect for your app
- ✅ **Fly.io** - Free tier, 3 VMs

**Current Status**: Your Render deployment should now work with the fixed `download_model.py` script!

---

## Test Your Deployment

Once deployed, test these endpoints:

1. **Health Check**:
   ```bash
   curl https://your-app.railway.app/
   ```

2. **API Docs**:
   ```
   https://your-app.railway.app/docs
   ```

3. **Form Templates**:
   ```bash
   curl https://your-app.railway.app/form-templates
   ```

---

## Next Steps

1. ✅ Push the latest code with `download_model.py`
2. ✅ Clear Railway build cache
3. ✅ Redeploy on Railway
4. ✅ Should work now!

The quote escaping issue is fixed! 🎉
