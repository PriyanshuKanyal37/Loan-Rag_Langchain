# Quick Start Guide - Render Deployment

## 🚀 5-Minute Deployment

### Step 1: Push to GitHub (2 min)

```bash
cd Loan_Final_rag
git init
git add .
git commit -m "Production ready deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/loan-rag-app.git
git push -u origin main
```

### Step 2: Deploy Backend (2 min)

1. Go to https://dashboard.render.com
2. Click **New +** → **Web Service**
3. Connect GitHub → Select your repo
4. Fill in:
   - **Name**: loan-rag-backend
   - **Build**: `pip install -r backend/requirements.txt`
   - **Start**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Click **Advanced** → Add environment variables:
   ```
   OPENAI_API_KEY=sk-proj-...
   QDRANT_URL=https://....gcp.cloud.qdrant.io:6333
   QDRANT_API_KEY=eyJhbGci...
   QDRANT_COLLECTION=loan_policy_chunks
   ENVIRONMENT=production
   ```
6. Click **Create Web Service**
7. **COPY THE URL** (e.g., https://loan-rag-backend.onrender.com)

### Step 3: Deploy Frontend (1 min)

1. Click **New +** → **Static Site**
2. Connect same GitHub repo
3. Fill in:
   - **Name**: loan-rag-frontend
   - **Root Directory**: `frontend`
   - **Build**: `npm install && npm run build`
   - **Publish**: `dist`
4. Add environment variable:
   ```
   VITE_API_BASE_URL=https://loan-rag-backend.onrender.com
   ```
   (Use the URL you copied in Step 2)
5. Click **Create Static Site**

### Step 4: Update Backend CORS

1. Go back to backend service
2. Add environment variable:
   ```
   FRONTEND_URL=https://loan-rag-frontend.onrender.com
   ```
   (Use your frontend URL)
3. Save (backend will auto-restart)

### Step 5: Test! 🎉

Open your frontend URL and test a refinance application!

---

## 📋 Environment Variables Needed

### Backend (5 variables)
- `OPENAI_API_KEY` - Your OpenAI key
- `QDRANT_URL` - From your Qdrant dashboard
- `QDRANT_API_KEY` - From your Qdrant dashboard
- `QDRANT_COLLECTION` - Use: `loan_policy_chunks`
- `ENVIRONMENT` - Use: `production`
- `FRONTEND_URL` - Your frontend URL (add after Step 3)

### Frontend (1 variable)
- `VITE_API_BASE_URL` - Your backend URL (from Step 2)

---

## ✅ Verification

Test with this scenario:
- Loan Type: Refinance
- Property Value: $720,000
- Current Loan: $680,000
- Reason: Debt Consolidation
- Annual Income: $170,000

Expected:
- ✅ DTI = 4.24x
- ✅ Top 3 lenders shown
- ✅ Complete policy citations

---

## 🆘 Common Issues

**Backend won't start?**
→ Check all 5 env variables are set

**Frontend can't connect?**
→ Check `VITE_API_BASE_URL` matches backend URL

**CORS errors?**
→ Add `FRONTEND_URL` to backend env vars

**RAG not working?**
→ Verify Qdrant connection (check backend logs)

---

## 📞 Need Help?

1. Check Render logs (click on service → Logs)
2. Review [README.md](README.md) for detailed docs
3. Check [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
