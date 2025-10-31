# Frontend Deployment Guide (Vercel)

## Your Frontend Tech Stack

- **Framework**: React 19.1.1
- **Build Tool**: Vite 7.1.7
- **Package Manager**: npm
- **Requirements File**: `package.json` ✅

## Deploy to Vercel (Recommended for Frontend)

### Option 1: Vercel Dashboard (Easiest)

#### Step 1: Go to Vercel
https://vercel.com/new

#### Step 2: Import Repository
1. Click "Add New..." → "Project"
2. Select your GitHub repository: `Loan-Rag_Langchain`
3. Click "Import"

#### Step 3: Configure Build Settings
```
Framework Preset: Vite
Root Directory: frontend
Build Command: npm run build
Output Directory: dist
Install Command: npm install
Node Version: 18.x (or latest)
```

#### Step 4: Add Environment Variables
Go to "Environment Variables" section and add:

```env
VITE_API_BASE_URL = https://loan-rag-backend.onrender.com
```

⚠️ **IMPORTANT**: Replace with your actual Render backend URL!

#### Step 5: Deploy
Click "Deploy" button and wait ~2 minutes ✅

---

### Option 2: Vercel CLI (Faster)

#### Step 1: Install Vercel CLI
```bash
npm install -g vercel
```

#### Step 2: Login
```bash
vercel login
```

#### Step 3: Navigate to Frontend
```bash
cd frontend
```

#### Step 4: Deploy
```bash
vercel --prod
```

#### Step 5: Set Environment Variable
```bash
vercel env add VITE_API_BASE_URL production
# When prompted, enter: https://loan-rag-backend.onrender.com
```

#### Step 6: Redeploy with New Env
```bash
vercel --prod
```

---

## Alternative: Deploy to Netlify

### Option 1: Netlify Dashboard

#### Step 1: Go to Netlify
https://app.netlify.com/start

#### Step 2: Import from Git
1. Click "Add new site" → "Import an existing project"
2. Choose GitHub
3. Select your repository

#### Step 3: Configure Build
```
Base directory: frontend
Build command: npm run build
Publish directory: frontend/dist
```

#### Step 4: Environment Variables
Add this in "Site configuration" → "Environment variables":
```
VITE_API_BASE_URL = https://loan-rag-backend.onrender.com
```

#### Step 5: Deploy
Click "Deploy site" ✅

---

### Option 2: Netlify CLI

#### Step 1: Install Netlify CLI
```bash
npm install -g netlify-cli
```

#### Step 2: Login
```bash
netlify login
```

#### Step 3: Initialize
```bash
cd frontend
netlify init
```

#### Step 4: Configure Build (when prompted)
```
Build command: npm run build
Directory to deploy: dist
```

#### Step 5: Set Environment Variable
```bash
netlify env:set VITE_API_BASE_URL https://loan-rag-backend.onrender.com
```

#### Step 6: Deploy
```bash
netlify deploy --prod
```

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────┐
│                                                 │
│  Frontend (Vercel/Netlify)                     │
│  • React + Vite                                │
│  • Static files                                │
│  • Global CDN                                  │
│  • Free hosting                                │
│  • URL: https://your-app.vercel.app            │
│                                                 │
└────────────────┬────────────────────────────────┘
                 │
                 │ API Calls
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│                                                 │
│  Backend (Render)                              │
│  • FastAPI + ML Models                         │
│  • Long-running process                        │
│  • Free tier                                   │
│  • URL: https://loan-rag-backend.onrender.com  │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Update Backend CORS for Production

After deploying frontend, update your backend's allowed origins:

### In backend/main.py:
```python
allowed_origins = [
    "http://localhost:5173",  # Local dev
    "https://your-app.vercel.app",  # Add your Vercel URL
    # or
    "https://your-app.netlify.app",  # Add your Netlify URL
]
```

Then redeploy your backend on Render.

---

## Verify Deployment

After deploying, test:

1. **Frontend loads**: Visit your Vercel/Netlify URL
2. **API connection works**: Try submitting a form
3. **No CORS errors**: Check browser console (F12)

---

## Troubleshooting

### Issue 1: API calls fail with CORS error
**Solution**: Add your frontend URL to backend CORS settings

### Issue 2: Environment variable not working
**Solution**:
- Vite requires `VITE_` prefix
- Redeploy after adding env vars
- Check browser console: `console.log(import.meta.env.VITE_API_BASE_URL)`

### Issue 3: Build fails
**Solution**:
- Check Node version (use 18.x or 20.x)
- Clear build cache and retry
- Check package.json scripts

---

## Cost Comparison

| Platform | Free Tier | Bandwidth | Build Time | Best For |
|----------|-----------|-----------|------------|----------|
| **Vercel** | Unlimited | 100GB/mo | Fast | React/Next.js |
| **Netlify** | Unlimited | 100GB/mo | Fast | Any framework |
| **Render Static** | Unlimited | 100GB/mo | Medium | Simple sites |

Both Vercel and Netlify are excellent for your frontend. Choose either!

---

## My Recommendation

**Use Vercel for Frontend + Render for Backend**

This gives you:
- ✅ Best performance for React apps
- ✅ Free hosting for both
- ✅ Auto-deploy from GitHub
- ✅ Global CDN
- ✅ Zero configuration

Total cost: **$0/month** 🎉
