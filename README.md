# ವಾಣಿ (Vaani) — KSP Crime Intelligence Console

Vaani is a conversational crime intelligence console built for
**Datathon 2026 — Karnataka State Police**.

It helps investigators explore crime intelligence through **voice and text**
in **English and Kannada**, while keeping investigation context, evidence,
governance and auditability in the same workflow.

**Challenge:** Intelligent Conversational AI for KSP Crime Database

**Live Demo:**
https://project-rainfall-60079338735.development.catalystserverless.in/app/index.html

**GitHub:**
https://github.com/Kusuma447/KSP-Vaani_Chatbot

---

## Problem

Crime investigation often requires connecting information scattered across
FIRs, accused records, cases, locations and investigation-process records.

Investigators need to move quickly from a question to connected evidence
without repeatedly switching between disconnected database views.

Vaani brings that investigation into one conversational workflow.

---

## What Vaani Does

### Investigation-first conversation

A single investigation can progress through:

**FIR → PERSON → CONNECTED CASES → LOCATION → PATTERNS → GAPS → NEXT ACTION**

Conversation context is preserved so follow-up questions can build on the
active investigation instead of restarting from scratch.

### Voice + bilingual interaction

- Voice input using the browser Web Speech API.
- English and Kannada interaction.
- Language can be switched during an investigation.
- Kannada-supported investigative intents are routed directly into the
  same intelligence pipeline.

### Deterministic crime intelligence

Supported investigative questions are handled by dedicated,
evidence-backed server-side engines rather than sending every question to
an LLM.

Examples include:

- FIR / case investigation
- Accused and person-network analysis
- Hotspot analysis
- Investigation gaps
- Chargesheet-related gaps
- Investigation status analysis
- Recommended next investigative actions
- Crime-pattern analytics
- Proactive evidence-backed crime signals

These paths produce reproducible results from the underlying KSP records.

### Bounded Gemini usage

Gemini is **not the authority over the crime database**.

When a request is genuinely open-ended and does not match a supported
deterministic intelligence path, Gemini can be used to generate a candidate
read-only ZCQL query.

Before execution, the generated query is validated against application
safety constraints.

This keeps LLM usage bounded while preserving conversational flexibility.

### Evidence and explainability

Vaani exposes the reasoning basis of each intelligence result through:

- Data sources
- Evidence basis
- Method
- Records considered
- Limitations
- Executed query where applicable

The system clearly distinguishes deterministic intelligence from
LLM-generated query paths.

### Authentication, RBAC and audit

Access to Vaani intelligence is protected through **Zoho Catalyst
Authentication**.

The application uses role-based access with an **Investigator** role and
records investigation activity through an audit trail.

Unauthenticated requests are rejected before protected intelligence is
executed.

### PDF case record

The active investigation conversation can be exported as a PDF for review
and record keeping.

---

## Architecture

```text
                Investigator
             Voice / Text Input
            English / Kannada
                     |
                     v
          +----------------------+
          |   Vaani Frontend     |
          | HTML / CSS / JS      |
          +----------+-----------+
                     |
                     v
          +----------------------+
          | Catalyst Auth /      |
          | RBAC / Audit         |
          +----------+-----------+
                     |
                     v
          +----------------------+
          | Conversation Context |
          +----------+-----------+
                     |
                     v
          +----------------------+
          |    Intent Router     |
          +----------+-----------+
                     |
          +----------+-----------+
          |                      |
          v                      v
 +-------------------+   +-------------------+
 | Deterministic     |   | Open-ended       |
 | Intelligence      |   | Request          |
 | Engines            |   |                  |
 +---------+---------+   +---------+---------+
           |                       |
           |                       v
           |               +---------------+
           |               |    Gemini     |
           |               | bounded ZCQL  |
           |               | generation    |
           |               +-------+-------+
           |                       |
           |                 Query validation
           |                       |
           +-----------+-----------+
                       |
                       v
             +--------------------+
             | Catalyst Data Store|
             | KSP Crime Records  |
             +---------+----------+
                       |
                       v
             Evidence + Method
             + Result + Context
                       |
                       v
                Investigator
                Core design principle

Vaani does not treat every question as an LLM-to-database problem.

For known investigative operations:

Question
   ↓
Intent
   ↓
Deterministic Engine
   ↓
KSP Data Store
   ↓
Evidence-backed Result

For genuinely open-ended questions:

Question
   ↓
No supported deterministic intent
   ↓
Gemini
   ↓
Candidate read-only ZCQL
   ↓
Validation
   ↓
KSP Data Store

This gives Vaani the flexibility of conversational AI without making the
core investigation workflow dependent on generated answers.

Key Differentiator

Vaani is not simply a chatbot placed on top of a database.

Its main design is:

The conversation is the interface; evidence-backed intelligence is the
foundation.

A single investigator question can progressively become a deeper
investigation while preserving context, evidence and governance.

Technology Stack
Layer	Technology
Frontend	HTML, CSS, JavaScript
Voice	Browser Web Speech API
Backend	Python 3.11
Serverless Platform	Zoho Catalyst
Backend Runtime	Catalyst Basic I/O Function
Database	Zoho Catalyst Data Store
Conversational AI	Google Gemini API
Query Language	ZCQL
Maps	Leaflet + OpenStreetMap
PDF Export	jsPDF
Authentication	Catalyst Hosted Authentication
Authorization	Catalyst role-based access
Audit	Application audit trail
Project Structure
KSP-Vaani_Chatbot/
│
├── client/
│   ├── index.html
│   ├── main.css
│   ├── main.js
│   └── client-package.json
│
├── functions/
│   └── ksp_chatboy_function/
│       ├── main.py
│       ├── catalyst-config.json
│       ├── requirements.txt
│       └── setup_db.py
│
├── catalyst.json
├── .gitignore
└── README.md
Security

The deployed application uses Catalyst Hosted Authentication.

Protected requests are validated for:

Authentication
Active user status
Authorized role
Data access scope
Audit recording

The application is designed to fail closed for unauthenticated or
unauthorized requests.

Evidence & Safety

Vaani is designed as an investigative intelligence aid, not as a system
that declares guilt.

For example, repeated appearance of a person across case records is treated
as a relationship signal, not as proof of culpability.

Similarly, hotspot and proactive-signal outputs are presented as
evidence-backed analytical indicators with stated limitations.

Local / Catalyst Deployment
Prerequisites
Node.js
Zoho Catalyst CLI
Catalyst account
Access to the required Catalyst project
Required environment variables for optional Gemini functionality
Clone
git clone https://github.com/Kusuma447/KSP-Vaani_Chatbot.git
cd KSP-Vaani_Chatbot
Catalyst

Authenticate with Catalyst and configure the project using the Catalyst
project configuration already present in the repository.

Deploy
catalyst deploy

For frontend-only updates:

catalyst deploy --only client

For backend updates, deploy the configured Catalyst function.

Demo Investigation Flow

The recommended demonstration follows one continuous investigation:

Investigate FIR-004
        ↓
Who is connected to Ravi Kumar?
        ↓
Show me the hotspot.
        ↓
What are the investigation gaps?
        ↓
What should the investigator check next?
        ↓
ಕನ್ನಡ
ಹಾಟ್‌ಸ್ಪಾಟ್ ತೋರಿಸಿ
        ↓
Evidence & Method
        ↓
Authentication / RBAC / Audit
        ↓
Save Conversation as PDF

This demonstrates how Vaani moves from a single question to a deeper,
evidence-backed investigation.

Prototype Scope

The prototype uses the available KSP reference crime dataset and focuses on
building a working conversational investigation workflow over the supported
crime-intelligence paths.

Results should be interpreted as investigative decision support and not as
a replacement for formal police investigation procedures.

Team

Kusuma Uppalapati
Jahnavi Kesanapalli

Sri Vasavi Engineering College (SVEC), Tadepalligudem
