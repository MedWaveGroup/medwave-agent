# MedWave Agent — Deployment Guide

## Architecture

```
Browser (Erich / Sterrenberg / Davide)
         │  login with email + password
         ▼
   Next.js Frontend  (no API keys here)
         │  fetch('/api/...')  with httpOnly cookie
         ▼
   Next.js API Routes  ◄── ALL secrets live here
         │
         ├── /api/auth/login       → issues JWT session cookie
         ├── /api/ai/chat          → Z.AI GLM-4.5 (ZAI_API_KEY)
         ├── /api/ai/assess-call   → Six-stage sales-call scorer
         ├── /api/leads/verify     → AI verify + email Davide
         ├── /api/leads/dedup      → GoHighLevel CRM check (GHL_API_KEY)
         └── /api/dispatch/email   → SMTP team emails
```

**Keys never touch the browser. Team members log in with email + password only.**

---

## Step 1 — Prerequisites

You need:
- A **GitHub account** (free) — github.com
- A **Vercel account** (free) — vercel.com
- **Node.js 18+** installed locally (nodejs.org) — only needed to test locally
- Your **Z.AI API key** (regenerated)
- Your **GHL API key** (regenerated, read-only)
- A **Gmail App Password** for info@medwavegroup.com

---

## Step 2 — Gmail App Password

The app sends emails via info@medwavegroup.com. Gmail requires an App Password (not your regular password).

1. Go to **myaccount.google.com**
2. Security → **2-Step Verification** (must be enabled)
3. Security → **App Passwords**
4. Select app: **Mail** / Select device: **Other** → name it "MedWave Agent"
5. Copy the 16-character password shown — you only see it once

---

## Step 3 — Push to GitHub

```bash
# In your terminal, navigate to the medwave-agent folder
cd medwave-agent

# Initialise git
git init
git add .
git commit -m "Initial MedWave Agent"

# Create a new repo on github.com (call it medwave-agent, set to Private)
# Then link and push:
git remote add origin https://github.com/YOUR_USERNAME/medwave-agent.git
git branch -M main
git push -u origin main
```

---

## Step 4 — Deploy to Vercel

1. Go to **vercel.com** → **Add New Project**
2. Click **Import Git Repository** → select `medwave-agent`
3. Framework Preset: **Next.js** (auto-detected)
4. Click **Deploy** — it will fail on first deploy (no env vars yet)

---

## Step 5 — Add Environment Variables in Vercel

In Vercel dashboard → your project → **Settings → Environment Variables**

Add each of these (copy from .env.example):

| Variable | Value |
|---|---|
| `ZAI_API_KEY` | Your Z.AI key |
| `GHL_API_KEY` | Your new GHL read-only key |
| `GHL_LOCATION_ID` | `QdLXaFEqrdF0JbVbpKLw` |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `info@medwavegroup.com` |
| `SMTP_PASS` | Your Gmail App Password (16 chars) |
| `ALERT_EMAIL` | `info@medwavegroup.com` |
| `AUTH_SECRET` | Run: `node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"` |
| `TEAM_PASSWORD_DAVIDE` | Choose a strong password for Davide |
| `TEAM_PASSWORD_FRANCOIS` | Choose a strong password for Francois |
| `TEAM_PASSWORD_ERICH` | Choose a strong password for Erich |
| `TEAM_PASSWORD_STERRENBERG` | Choose a strong password for Sterrenberg |
| `TEAM_PASSWORD_HAZEL` | Choose a strong password for Hazel |
| `TEAM_PASSWORD_AZOLA` | Choose a strong password for Azola |

**Important:** Set environment to **Production, Preview, Development** for all variables.

---

## Step 6 — Redeploy

In Vercel → **Deployments** → click the three dots on the latest → **Redeploy**

Or just push any change to GitHub — Vercel auto-deploys on every push.

---

## Step 7 — Access the App

Your app will be live at:
```
https://medwave-agent.vercel.app
```
(or a custom domain if you set one)

Share the URL + their password with Erich and Sterrenberg.

**Login credentials:**
- Davide: info@medwavegroup.com + TEAM_PASSWORD_DAVIDE value
- Francois: francois@medwavegroup.com + TEAM_PASSWORD_FRANCOIS value
- Erich: erich@medwavegroup.com + TEAM_PASSWORD_ERICH value
- Sterrenberg: sterrenberg@medwavegroup.com + TEAM_PASSWORD_STERRENBERG value
- Hazel: hazel@medwavegroup.com + TEAM_PASSWORD_HAZEL value
- Azola: azola@medwavegroup.com + TEAM_PASSWORD_AZOLA value

---

## Step 8 — Custom Domain (Optional)

In Vercel → Settings → Domains → Add `agent.medwavegroup.com`

Then in your domain registrar (wherever medwavegroup.com is registered), add a CNAME record:
```
Name:  agent
Value: cname.vercel-dns.com
```

---

## Local Development

```bash
# Clone and install
git clone https://github.com/YOUR_USERNAME/medwave-agent.git
cd medwave-agent
npm install

# Copy env template
cp .env.example .env.local
# Fill in .env.local with real values

# Run locally
npm run dev
# Open http://localhost:3000
```

---

## Security Notes

- ✅ API keys stored as Vercel env vars — never in code or browser
- ✅ Sessions use httpOnly cookies — JavaScript cannot access them
- ✅ JWT tokens expire after 24 hours — team re-logs in daily
- ✅ GHL key is read-only — cannot modify CRM data
- ✅ All API routes verify session before executing
- ✅ .gitignore excludes all .env files

---

## File Structure

```
medwave-agent/
├── src/
│   ├── pages/
│   │   ├── index.tsx          ← Main app (frontend only, no keys)
│   │   └── _app.tsx
│   └── lib/
│       └── auth.ts            ← JWT session verification helper
├── api/
│   ├── auth/
│   │   ├── login.ts           ← Team login → issues cookie
│   │   └── logout.ts
│   ├── ai/
│   │   ├── chat.ts            ← GLM-4.5 proxy (ZAI_API_KEY)
│   │   └── assess-call.ts     ← Six-stage sales-call scorer (ZAI_API_KEY)
│   ├── leads/
│   │   ├── verify.ts          ← AI verify + email (ZAI + SMTP)
│   │   └── dedup.ts           ← GHL CRM dedup (GHL_API_KEY)
│   └── dispatch/
│       └── email.ts           ← Team email sender (SMTP)
├── .env.example               ← Template — never commit .env.local
├── .gitignore
├── next.config.js
├── package.json
└── tsconfig.json
```

---

## Cost Summary (monthly)

| Service | Plan | Cost |
|---|---|---|
| Vercel | Hobby (free) | R0 |
| GitHub | Free | R0 |
| Z.AI GLM-4.5-Air | Pay per use | ~R50–150 |
| Gmail SMTP | Free (App Password) | R0 |
| **Total** | | **~R50–150/month** |

---

## Call Coach (Sales Framework Scorer)

Opens at **Dashboard → Call Coach** in the UI. Paste a Google Meet transcript
(or upload a `.txt` / `.vtt`) and click **Assess Call**. The backend scores the
call against the MedWave Six-Stage Framework and returns:

- Stage-by-stage breakdown (Intro & Fit → PPP Discovery → Diagnosis → Permission
  to Pitch → Value Pitch → Close)
- Strengths and gaps (each with a concrete fix)
- Style alignment — Alex Hormozi vs. Jeremy Minor
- Overall score (1–10) with rubric label
- One-sentence coaching direction for the next call

The rubric lives in `api/ai/assess-call.ts` — edit the `FRAMEWORK_PROMPT`
constant to iterate on what the rubric rewards as the team learns what top
closers actually do.

---

## Questions?

Contact: info@medwavegroup.com
