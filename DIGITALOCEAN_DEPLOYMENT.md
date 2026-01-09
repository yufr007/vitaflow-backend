# DigitalOcean Python Backend Deployment Guide

## Current Backend Status ✅

Your `vitaflow-backend` directory is **correctly structured** for Python deployment:

```
vitaflow-backend/
├── main.py ✅ (FastAPI app with all routes)
├── requirements.txt ✅ (All Python dependencies)
├── config.py ✅ (Settings management)
├── database.py ✅ (MongoDB connection)
├── .gitignore ✅
├── .env.example ✅
└── app/
    ├── __init__.py ✅
    ├── models/ ✅ (User, Auth, etc.)
    ├── routes/ ✅ (auth, user, formcheck, workout, mealplan, shopping, coaching, subscription)
    ├── schemas/ ✅
    ├── services/ ✅
    └── utils/ ✅
```

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `vitaflow-backend`
3. Description: "VitaFlow AI Fitness Backend - Python/FastAPI"
4. **Public** (free tier) or **Private** (if you have paid plan)
5. **DO NOT** initialize with README, .gitignore, or license
6. Click **Create repository**

## Step 2: Push Backend to GitHub

After creating the repo on GitHub, run:

```powershell
cd 'c:\Users\chris\Documents\VItaFlow\vitaflow-backend'

# Add the remote (use your actual GitHub repo URL)
git remote add origin https://github.com/yufr007/vitaflow-backend.git

# Rename branch to main
git branch -M main

# Push to GitHub
git push -u origin main
```

## Step 3: Delete Old DigitalOcean App

1. Go to https://cloud.digitalocean.com/apps
2. Click on **vitaflow-backend** app
3. Go to **Settings** → scroll to bottom
4. Click **Destroy App**
5. Type the app name to confirm
6. Click **Destroy**

## Step 4: Create New App (Python Stack)

1. Go to https://cloud.digitalocean.com/apps
2. Click **Create** → **Apps**
3. Select **GitHub**
4. Authorize GitHub if needed
5. Choose **vitaflow-backend** repository
6. Click **Next**

## Step 5: Configure Build & Run

DigitalOcean should auto-detect Python. Verify these settings:

### Build Configuration
- **Source Branch**: `main`
- **Build Command**: Leave empty (auto-detects from requirements.txt)
- **Autodeploy**: ✅ Yes

### Run Configuration
- **Run Command**: `uvicorn main:app --host 0.0.0.0 --port 8080`
- **HTTP Port**: `8080`
- **Instance Size**: **Basic** ($5/month for 512MB RAM)

## Step 6: Environment Variables

Add these in the DigitalOcean app settings:

| Variable | Value |
|----------|-------|
| `MONGODB_URL` | Your MongoDB connection string |
| `SECRET_KEY` | Generate with: `openssl rand -hex 32` |
| `ENV` | `production` |
| `DEBUG` | `False` |
| `CORS_ORIGINS` | `https://vitaflow.fitness,https://www.vitaflow.fitness` |

### Get Your MongoDB URL

If you don't have one yet:
1. Go to https://cloud.mongodb.com/
2. Create a free cluster
3. Click **Connect** → **Connect your application**
4. Copy the connection string
5. Replace `<password>` with your database password

### Generate Secret Key

Run in PowerShell:
```powershell
# Option 1: Using OpenSSL (if installed)
openssl rand -hex 32

# Option 2: Using Python
python -c "import secrets; print(secrets.token_hex(32))"

# Option 3: Quick random (less secure, but works)
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | % {[char]$_})
```

## Step 7: Deploy

1. Click **Next** → **Next**
2. Review settings
3. Click **Create Resources**
4. Wait 5-10 minutes for deployment

## Step 8: Add Custom Domain

After successful deployment:

1. Go to **Settings** → **Domains**
2. Click **Add Domain**
3. Enter: `api.vitaflow.fitness`
4. DigitalOcean will show DNS records to add

### Add DNS Records in Your Domain Provider

Add these records where you manage `vitaflow.fitness`:

| Type | Name | Value |
|------|------|-------|
| CNAME | api | `<your-app>.ondigitalocean.app` |

DigitalOcean will auto-provision SSL certificate (takes 10-15 minutes).

## Step 9: Test Deployment

After DNS propagation (5-30 minutes):

```bash
# Test health endpoint
curl https://api.vitaflow.fitness/health

# Should return:
# {"status":"ok","service":"VitaFlow API","domain":"vitaflow.fitness","env":"production"}

# Test docs
open https://api.vitaflow.fitness/docs
```

## Step 10: Update Frontend

Update your frontend to use the new API URL:

```env
VITE_API_URL=https://api.vitaflow.fitness
```

## Why This Will Work Now

### ❌ Previous Setup (Failed)
- DigitalOcean detected `package.json` → initialized as **Node.js**
- When you ran `uvicorn`, Python wasn't installed
- Dependencies never installed → import errors

### ✅ New Setup (Will Succeed)
- Repository contains **only Python code**
- DigitalOcean detects `requirements.txt` → initializes as **Python**
- Automatically runs `pip install -r requirements.txt`
- `uvicorn` command works because Python environment is ready

## Troubleshooting

### Deployment Failed
Check logs in DigitalOcean:
1. Go to your app → **Runtime Logs**
2. Look for import errors or missing dependencies

### Can't Connect to MongoDB
- Verify `MONGODB_URL` environment variable is set
- Check MongoDB Atlas network access allows DigitalOcean IPs (0.0.0.0/0 for testing)
- Verify database user credentials

### CORS Errors
- Check `CORS_ORIGINS` includes your frontend domain
- Verify frontend is making requests to correct API URL

### App Crashes After Startup
- Check if all routes are importing correctly
- Verify all dependencies in `requirements.txt` match your code
- Check Runtime Logs for Python errors

## Current Backend Details

Your `main.py` includes:
- ✅ FastAPI app with CORS configured
- ✅ MongoDB connection on startup
- ✅ All 8 route modules registered (auth, user, formcheck, workout, mealplan, shopping, coaching, subscription)
- ✅ Health check endpoint at `/health`
- ✅ API docs at `/docs`

Your `requirements.txt` includes:
- ✅ FastAPI 0.104.1
- ✅ Uvicorn with standard extras
- ✅ Motor (async MongoDB)
- ✅ Beanie (ODM)
- ✅ Pydantic Settings
- ✅ JWT auth (python-jose)
- ✅ Password hashing (passlib)
- ✅ Stripe integration
- ✅ Google Cloud Storage
- ✅ Google Generative AI

## Next Steps After Deployment

1. ✅ Deploy backend to DigitalOcean
2. ✅ Add custom domain `api.vitaflow.fitness`
3. ✅ Update frontend environment variables
4. ✅ Test all API endpoints
5. ✅ Monitor logs for any errors
6. 🚀 Go live!

---

**Ready to proceed?**

1. Create the GitHub repo: https://github.com/new
2. Push your code (commands above in Step 2)
3. Create new DigitalOcean app pointing to the Python repo
4. Deploy! 🚀
