# NEXORA ERP — Vercel Deployment Guide

NEXORA ERP is pre-configured to deploy on **Vercel** using two production patterns:

1. **Option 1 (Unified Single-Project Vercel Deployment — Fastest)**:
   Deploys both the Glassmorphism Web Application Portal and the FastAPI `/api/v1/*` backend together on a single Vercel URL using [vercel.json](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/vercel.json) and [api/index.py](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/api/index.py).
2. **Option 2 (Decoupled Frontend on Vercel + Managed PostgreSQL on Neon/Supabase)**:
   Connects the Vercel deployment to a persistent cloud PostgreSQL database (`DATABASE_URL`) so all multi-tenant data persists permanently across serverless cold starts.

---

## Step-by-Step Deployment to Vercel

### Step 1: Push the Repository to GitHub
```bash
git init
git add .
git commit -m "feat: complete NEXORA ERP full-stack platform with Vercel support"
git branch -M main
git remote add origin https://github.com/<your-username>/nexora-erp.git
git push -u origin main
```

### Step 2: Import Project in Vercel Dashboard
1. Go to https://vercel.com/new and select your `nexora-erp` GitHub repository.
2. Leave **Root Directory** as `./` (root). Vercel will automatically detect [vercel.json](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/vercel.json), [api/index.py](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/api/index.py), and [requirements.txt](file:///c:/Users/abdur/OneDrive/Desktop/NEXORA-AI/requirements.txt).

### Step 3: Configure Environment Variables (Recommended for Persistent PostgreSQL)
In the Vercel project settings (**Settings → Environment Variables**), add:
- `SECRET_KEY`: A strong 64-character random string.
- `DATABASE_URL`: Your managed PostgreSQL connection string from **Vercel Storage (Neon)** or **Supabase** (e.g., `postgresql+psycopg://user:password@ep-xyz.region.aws.neon.tech/neondb?sslmode=require`).
  - *Note*: If you deploy without setting `DATABASE_URL` first, NEXORA ERP automatically falls back to `/tmp/nexora_erp.db` and seeds **Nexora Demo Holdings** on cold start so your live demo works immediately out of the box!

### Step 4: Deploy via Vercel CLI (Alternative to Dashboard)
```bash
npx vercel
# For production:
npx vercel --prod
```
