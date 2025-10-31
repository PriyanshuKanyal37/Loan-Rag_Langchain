# Railway Deployment Guide

## Error Fixed! ✅

The error you encountered was:
```
NameError: name 'sentence' is not defined
```

**Cause:** Railway stripped quotes from the model download command in the build phase.

**Solution:** Created `backend/download_model.py` script instead of inline Python command.

---

## Prerequisites

1. Railway account: https://railway.app
2. GitHub repository connected
3. Credit card (required even for free tier)

---

## Deploy to Railway

### Method 1: Railway Dashboard (Recommended)

#### Step 1: Create New Project
1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your repository: `Loan-Rag_Langchain`
4. Click "Deploy Now"

#### Step 2: Configure Root Directory
1. Click on your service
2. Go to "Settings" tab
3. Set **Root Directory**: `backend`
4. Click "Save"

#### Step 3: Configure Build Command
In Settings → Build:
```bash
pip install -r requirements.txt && python download_model.py
```

#### Step 4: Configure Start Command
In Settings → Deploy:
```bash
python -m uvicorn main:app --host 0.0.0.0 --port $PORT
```

#### Step 5: Add Environment Variables
Go to "Variables" tab and add:

```env
OPENAI_API_KEY=your_openai_key_here
QDRANT_URL=your_qdrant_url_here
QDRANT_API_KEY=your_qdrant_api_key_here
QDRANT_COLLECTION=loan_policy_chunks
ENVIRONMENT=production
```

#### Step 6: Deploy
Railway will automatically deploy. Wait 3-5 minutes for build.

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
