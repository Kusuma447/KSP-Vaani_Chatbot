# ವಾಣಿ (Vaani) — KSP Crime Intelligence Console

A bilingual (English + Kannada) voice-driven conversational AI for querying the KSP crime database using natural language, built for **Datathon 2026 — Karnataka State Police**, challenge track *"Intelligent Conversational AI for KSP Crime Database."*

**Live demo:** https://project-rainfall-60079338735.development.catalystserverless.in/app/index.html

## Problem Statement

Investigators and analysts need to query crime records (FIRs, complainants, case status, stations) quickly, without writing SQL or navigating complex database UIs — and increasingly, in their own language rather than only English.

## What This Prototype Does

- **Voice input** in English and Kannada using the Web Speech API — toggle between languages live.
- **Natural language understanding** powered by Google's Gemini API — user questions (in either language) are converted into real SQL queries against the crime database, not matched against a fixed keyword list. Handles relative dates, follow-up questions, and free-form phrasing.
- **Conversation memory** — follow-up questions ("what about pending ones?") reuse context from the previous query without the user repeating themselves.
- **Explainable AI** — every answer shows the exact SQL query that was generated and run, so results are auditable and transparent, not a black box.
- **Save conversation as PDF** — the full query history (questions, generated SQL, and results) can be exported to PDF locally for case documentation.
- **Deployed on Zoho Catalyst** — both the backend (Catalyst Basic I/O Python function) and frontend (Catalyst Web Client) are live on Catalyst's serverless infrastructure, per the mandatory deployment requirement.

## Tech Stack

| Layer | Technology |
|---|---|
| Voice input | Web Speech API (browser-native, English + Kannada) |
| NLP → SQL | Google Gemini API (`gemini-flash-latest`) |
| Backend | Python 3.11, Zoho Catalyst Basic I/O Function |
| Database | SQLite |
| Frontend | HTML/CSS/JavaScript, Zoho Catalyst Web Client |
| PDF export | jsPDF (client-side) |
| Deployment | Zoho Catalyst (Functions + Web Client Hosting) |

## Project Structure
functions/ksp_chatboy_function/
main.py — Backend: receives query text, calls Gemini to generate SQL, runs it against the DB, returns results
setup_db.py — Creates the SQLite database with sample complaint records
police.db — Sample crime database (fake data for prototype demo)
catalyst-config.json — Catalyst function config (API key stored as an environment variable, not hardcoded)
requirements.txt — Python dependencies

client/ksp-chatbot-client/
index.html — Frontend: voice/text input, language toggle, result cards, PDF export

## Setup & Execution (Local Development)

1. **Install the Catalyst CLI:**
npm install -g zcatalyst-cli
catalyst login
2. **Clone this repo and initialize:**
git clone https://github.com/Kusuma447/KSP-Vaani_Chatbot.git
cd KSP-Vaani_Chatbot
catalyst init
3. **Set up the database:**
cd functions/ksp_chatboy_function
python setup_db.py
4. **Add your own Gemini API key** in `functions/ksp_chatboy_function/catalyst-config.json`:
```json
   "env_variables": {
     "GEMINI_API_KEY": "your-key-here"
   }
```
   Get a free key at [Google AI Studio](https://aistudio.google.com).

5. **Test locally:**
6. **Deploy:**
## Roadmap — What's Next (Beyond This Prototype)

The full challenge spec outlines 10 pillars (network analysis, offender profiling, socio-demographic insights, financial crime tracing, predictive forecasting, RBAC, etc.). This prototype focuses on building a genuinely working, deployed core — the Conversational Intelligence Interface and Explainable AI pillars — rather than partially faking all ten. Planned next steps if shortlisted for the refinement phase:

- Criminal network & relationship visualization
- Crime pattern/trend analytics with charts
- Offender risk scoring
- Role-based access control and audit logging
- Expanded, richer dataset matching KSP's actual schema

## Team

Kusuma Uppalapati , Jahnavi Kesanapalli — Sri Vasavi Engineering College (SVEC), Tadepalligudem