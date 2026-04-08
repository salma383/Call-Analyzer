# MyVA Call Analyzer — Setup & Deployment Guide

## What This Does
Uploads a call recording → transcribes it via Groq Whisper → scores the agent
against your exact client criteria → gives coaching notes, red flags, and a
disposition suggestion.

Supports all 11+ MyVA clients/campaigns out of the box.

---

## Files
```
call-analyzer/
├── app.py          ← main Streamlit app
├── criteria.py     ← all client criteria (checklist, red flags, coaching)
├── requirements.txt
└── README.md
```

---

## Option A — Run Locally (fastest to test)

1. Install Python 3.10+ if you don't have it
2. Open terminal in the `call-analyzer` folder
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the app:
   ```
   streamlit run app.py
   ```
5. Opens at http://localhost:8501

---

## Option B — Deploy on Streamlit Community Cloud (FREE, shareable URL)

This gives you a URL like `https://myva-calls.streamlit.app` that anyone
can open — no installs, no domain purchase needed.

### Steps:

1. **Create a GitHub account** (free) at github.com if you don't have one

2. **Create a new repository** — name it `myva-call-analyzer` (private is fine)

3. **Upload these 3 files** to the repo:
   - `app.py`
   - `criteria.py`
   - `requirements.txt`

4. **Go to** https://share.streamlit.io and sign in with GitHub

5. Click **"New app"** → select your repo → select `app.py` as the main file

6. Click **Deploy** — takes ~2 minutes

7. **Share the URL** with your ops managers — they just open it in a browser,
   enter the Groq API key, and start analyzing calls

### Groq API Key
- Each user enters their own key in the sidebar (safe — never stored)
- OR you can add it as a Streamlit secret so nobody has to type it:
  1. In Streamlit Cloud dashboard → your app → Settings → Secrets
  2. Add: `GROQ_API_KEY = "gsk_your_key_here"`
  3. Then update app.py line 1 to read:
     ```python
     import streamlit as st
     api_key = st.secrets.get("GROQ_API_KEY", "")
     ```
  4. Remove the API key text input from the sidebar

---

## Adding or Updating Client Criteria
Open `criteria.py` and find the client in `CLIENT_CRITERIA`.
Each client has:
- `checklist` — yes/no questions scored against the call
- `hard_disqualifiers` — instant fail conditions
- `red_flags` — patterns to watch for
- `coaching_focus` — standard coaching points always shown
- `script_notes` — context for the AI scorer

---

## Supported Audio Formats
MP3, MP4, M4A, WAV, OGG, FLAC, WEBM
(Max file size: 25MB per Groq Whisper limit)

---

## Cost Estimate
Groq API is free tier for moderate usage:
- Whisper transcription: ~$0.00 per minute (free tier generous)
- LLaMA scoring: ~$0.001 per call analysis
- For a team of 10 agents analyzing 5 calls/day: essentially free

---

Built by Claude for Salma @ MyVA
