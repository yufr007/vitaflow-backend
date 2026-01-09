# Backend Deployment - Quick Steps

## 1️⃣ Create GitHub Repo
**URL**: https://github.com/new
- Name: `vitaflow-backend`
- Description: "VitaFlow AI Fitness Backend - Python/FastAPI"
- **Public** repository
- **DO NOT** initialize with any files
- Click **Create repository**

## 2️⃣ Push Code to GitHub

```powershell
cd 'c:\Users\chris\Documents\VItaFlow\vitaflow-backend'
git remote add origin https://github.com/yufr007/vitaflow-backend.git
git push -u origin main
```

## 3️⃣ Delete Old DigitalOcean App
- Go to: https://cloud.digitalocean.com/apps
- Click **vitaflow-backend** → **Settings** → **Destroy App**

## 4️⃣ Create New DigitalOcean App
- https://cloud.digitalocean.com/apps → **Create App**
- Source: **GitHub** → **vitaflow-backend** repo
- Branch: `main`

## 5️⃣ Configure Settings

**Run Command**:
```
uvicorn main:app --host 0.0.0.0 --port 8080
```

**HTTP Port**: `8080`

**Instance Size**: Basic ($5/month)

## 6️⃣ Environment Variables

```
MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/vitaflow
SECRET_KEY=<generate with: openssl rand -hex 32>
ENV=production
DEBUG=False
CORS_ORIGINS=https://vitaflow.fitness,https://www.vitaflow.fitness
```

## 7️⃣ Add Domain
- **Settings** → **Domains** → **Add Domain**
- Enter: `api.vitaflow.fitness`
- Add CNAME record in your DNS provider

## 8️⃣ Test

```bash
curl https://api.vitaflow.fitness/health
```

Expected: `{"status":"ok","service":"VitaFlow API"}`

---

**Backend is Ready** ✅
- Python/FastAPI structure correct
- All routes registered
- Dependencies listed
- Ready to deploy to DigitalOcean

**What Changed**:
- ❌ Old: Node.js environment couldn't run `uvicorn`
- ✅ New: Pure Python repo → DigitalOcean auto-detects Python → installs dependencies → runs uvicorn successfully
