# Deployment Checklist

## Pre-Deployment

- [ ] All PDFs processed and uploaded to Qdrant Cloud
- [ ] Backend tested locally with correct DTI/LVR calculations
- [ ] Frontend tested locally and connects to backend
- [ ] Environment variables documented in .env.example files
- [ ] Code committed to GitHub repository

## Backend Deployment (Render)

- [ ] Created Web Service on Render
- [ ] Set Build Command: `pip install -r backend/requirements.txt`
- [ ] Set Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- [ ] Added OPENAI_API_KEY environment variable
- [ ] Added QDRANT_URL environment variable
- [ ] Added QDRANT_API_KEY environment variable
- [ ] Added QDRANT_COLLECTION=loan_policy_chunks
- [ ] Added ENVIRONMENT=production
- [ ] Backend deployed successfully
- [ ] Backend health check passing
- [ ] Copied backend URL for frontend configuration

## Frontend Deployment (Render)

- [ ] Created Static Site on Render
- [ ] Set Root Directory: `frontend`
- [ ] Set Build Command: `npm install && npm run build`
- [ ] Set Publish Directory: `dist`
- [ ] Added VITE_API_BASE_URL with backend URL
- [ ] Frontend deployed successfully
- [ ] Frontend loads correctly
- [ ] Copied frontend URL for backend CORS

## Post-Deployment

- [ ] Updated backend with FRONTEND_URL environment variable
- [ ] Backend redeployed with updated CORS
- [ ] Tested full application flow:
  - [ ] Submit Purchase Application
  - [ ] Submit Refinance Application
  - [ ] Submit SMSF Application
  - [ ] Verify DTI calculations correct
  - [ ] Verify LVR calculations correct
  - [ ] Verify top 3 lenders shown
  - [ ] Verify policy citations complete
  - [ ] No backend instructions visible to clients

## Verification Tests

Test with this refinance scenario:
- Property Value: $720,000
- Current Loan: $680,000
- Credit Cards: $15,000
- Personal Loans: $20,000
- Reason: "Debt Consolidation"
- Annual Income: $170,000

Expected Results:
- ✅ DTI = 4.24x ($720,000 / $170,000)
- ✅ LVR calculated correctly
- ✅ Top 3 lenders shown
- ✅ Complete policy citations
- ✅ Client-friendly output

## Troubleshooting

If issues occur:
1. Check Render deployment logs
2. Verify environment variables
3. Test Qdrant connection
4. Check CORS configuration
5. Review frontend console errors

## Rollback Plan

If deployment fails:
1. Revert to previous GitHub commit
2. Redeploy from working commit
3. Check logs for specific errors
4. Fix issues locally first
5. Redeploy after testing
