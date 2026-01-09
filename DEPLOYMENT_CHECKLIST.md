# ✅ Backend Deployment Checklist

## Pre-Deployment Status
- ✅ Python backend structure verified
- ✅ `main.py` with FastAPI app configured
- ✅ `requirements.txt` with all dependencies
- ✅ All 8 route modules present (auth, user, formcheck, workout, mealplan, shopping, coaching, subscription)
- ✅ Database connection configured
- ✅ CORS settings ready for production
- ✅ Git repo initialized locally
- ✅ Deployment documentation created

## GitHub Setup
- [ ] 1. Create GitHub repository: https://github.com/new
  - Name: `vitaflow-backend`
  - Visibility: Public
  - No README, .gitignore, or license
- [ ] 2. Push code to GitHub:
  ```bash
  cd 'c:\Users\chris\Documents\VItaFlow\vitaflow-backend'
  git remote add origin https://github.com/yufr007/vitaflow-backend.git
  git push -u origin main
  ```
- [ ] 3. Verify repo visible at: https://github.com/yufr007/vitaflow-backend

## DigitalOcean Cleanup
- [ ] 4. Delete old Node.js app:
  - https://cloud.digitalocean.com/apps
  - Select **vitaflow-backend**
  - Settings → Destroy App

## DigitalOcean Python Deployment
- [ ] 5. Create new app:
  - https://cloud.digitalocean.com/apps → Create App
  - Source: GitHub → vitaflow-backend repo
  - Branch: main
  - Click Next

- [ ] 6. Verify build detection:
  - Should show: **Python** (not Node.js)
  - Build command: auto-detected from requirements.txt

- [ ] 7. Configure run settings:
  - Run command: `uvicorn main:app --host 0.0.0.0 --port 8080`
  - HTTP Port: `8080`
  - Instance Size: Basic ($5/month)

## Environment Variables Setup
- [ ] 8. Add environment variables:
  - `MONGODB_URL`: (your MongoDB connection string)
  - `SECRET_KEY`: (generate with `openssl rand -hex 32`)
  - `ENV`: `production`
  - `DEBUG`: `False`
  - `CORS_ORIGINS`: `https://vitaflow.fitness,https://www.vitaflow.fitness`

- [ ] 9. Get MongoDB URL:
  - https://cloud.mongodb.com/
  - Create free cluster if needed
  - Get connection string

- [ ] 10. Generate secret key:
  ```bash
  openssl rand -hex 32
  # OR
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

## Deploy
- [ ] 11. Click **Create Resources**
- [ ] 12. Wait for deployment (5-10 minutes)
- [ ] 13. Check deployment logs for errors
- [ ] 14. Test default URL:
  ```bash
  curl https://<your-app>.ondigitalocean.app/health
  ```

## Custom Domain
- [ ] 15. Add custom domain:
  - Settings → Domains → Add Domain
  - Enter: `api.vitaflow.fitness`

- [ ] 16. Update DNS:
  - Add CNAME record in your DNS provider:
  - Type: CNAME
  - Name: api
  - Value: `<your-app>.ondigitalocean.app`

- [ ] 17. Wait for SSL certificate (10-15 minutes)

- [ ] 18. Test custom domain:
  ```bash
  curl https://api.vitaflow.fitness/health
  ```

## Frontend Integration
- [ ] 19. Update frontend environment:
  ```
  VITE_API_URL=https://api.vitaflow.fitness
  ```

- [ ] 20. Test frontend connection to backend

- [ ] 21. Test all API endpoints from frontend

## Final Verification
- [ ] 22. API docs accessible: https://api.vitaflow.fitness/docs
- [ ] 23. Health check working: https://api.vitaflow.fitness/health
- [ ] 24. Authentication endpoints working
- [ ] 25. Database connections successful
- [ ] 26. No CORS errors in browser console
- [ ] 27. Monitor logs for 24 hours

## 🚀 Production Ready!
- [ ] 28. Backend live at: `https://api.vitaflow.fitness`
- [ ] 29. Frontend live at: `https://vitaflow.fitness`
- [ ] 30. All features working end-to-end

---

## Current Status: Ready to Deploy ✅

Your backend is **100% ready** for DigitalOcean Python deployment.

**Next Action**: Create GitHub repo and push code (Steps 1-3)

**Why This Will Work**:
- ✅ Pure Python repository (no package.json to confuse DigitalOcean)
- ✅ Correct `requirements.txt` with all dependencies
- ✅ Proper `main.py` with uvicorn-compatible FastAPI app
- ✅ All routes and models structured correctly

**Documentation**:
- Full guide: `DIGITALOCEAN_DEPLOYMENT.md`
- Quick reference: `QUICK_DEPLOY.md`
- This checklist: `DEPLOYMENT_CHECKLIST.md`
