# Deployment Guide - Render Only

This project is configured to deploy on **Render** (free tier).

---

## Quick Deploy

### 1. Push to GitHub
```bash
git push origin main
```

### 2. Go to Render Dashboard
https://dashboard.render.com

### 3. Backend Setup (Already Configured)
- Service name: `loan-rag-backend`
- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt && python download_model.py`
- Start Command: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT --timeout-keep-alive 60`

**Environment Variables Required:**
```
OPENAI_API_KEY=your_key
QDRANT_URL=your_url
QDRANT_API_KEY=your_key
QDRANT_COLLECTION=loan_policy_chunks
ENVIRONMENT=production
```

### 4. Test
Once deployed, visit:
- Health: `https://loan-rag-backend.onrender.com/`
- API Docs: `https://loan-rag-backend.onrender.com/docs`

---

## Files You Need

✅ `render.yaml` - Render configuration
✅ `backend/requirements.txt` - Python dependencies
✅ `backend/download_model.py` - Pre-downloads ML model during build
✅ `backend/main.py` - FastAPI application
✅ `backend/ai_pipeline.py` - ML logic

**That's it!**

---

## Troubleshooting

### Build takes long time
**Normal!** Model download takes 5-10 minutes first time.

### Port binding timeout
**Fixed!** Using `download_model.py` during build phase, not startup.

### Environment variables missing
Add them in Render Dashboard → Settings → Environment Variables

---

## Frontend (Optional)

Deploy frontend separately to Vercel/Netlify:
- Just point them to the `frontend/` folder
- Add env var: `VITE_API_BASE_URL=https://loan-rag-backend.onrender.com`

---

**Current Status: Backend deploys successfully on Render Free tier ✅**
