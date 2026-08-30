# ವಾಣಿ (Vaani) — KSP Crime Intelligence Console

Vaani is a conversational crime intelligence console built for **Datathon 2026 — Karnataka State Police**.

It turns a single investigator question into a connected investigation across **FIRs, people, cases, locations, patterns, investigation gaps and next actions** through a context-aware voice and text interface in **English and Kannada**.

**Challenge:** Intelligent Conversational AI for KSP Crime Database

**Live Demo:**  
https://project-rainfall-60079338735.development.catalystserverless.in/app/index.html

**GitHub:**  
https://github.com/Kusuma447/KSP-Vaani_Chatbot

---

## Problem

Crime investigation often requires connecting information scattered across FIRs, accused records, cases, locations and investigation-process records.

Investigators need to move from a question to connected evidence quickly, without repeatedly switching between disconnected database views.

Vaani brings these investigation steps into one conversational workflow.

---

## What Vaani Does

### Investigation-first conversation

A single investigation can progress through:

**FIR → PERSON → CONNECTED CASES → LOCATION → PATTERNS → GAPS → NEXT ACTION**

Conversation context is preserved so follow-up questions can build on the active investigation instead of restarting from scratch.

### Voice + bilingual interaction

- Voice input using the browser Web Speech API.
- English and Kannada interaction.
- Language can be switched during an investigation.
- Supported Kannada investigative intents use the same investigation pipeline as English.

### Deterministic crime intelligence

Vaani does not send every question to an LLM.

Supported investigative operations are handled by dedicated, evidence-backed server-side engines.

Examples include:

- FIR / case investigation
- Accused and person-network analysis
- Connected case analysis
- Hotspot analysis
- Investigation gaps
- Chargesheet-related gaps
- Investigation status analysis
- Recommended next investigative actions
- Recurring crime-pattern analysis
- Proactive evidence-backed crime signals

These paths operate directly against the underlying KSP records and produce reproducible results.

### Bounded Gemini usage

Gemini is used for **genuinely open-ended requests that fall outside the supported deterministic investigative workflows**.

The flow is:

```text
Question
   ↓
Intent Router
   ↓
Supported investigative intent?
   ├── YES → Deterministic intelligence engine
   │          ↓
   │       KSP Data Store
   │
   └── NO  → Gemini
              ↓
          Candidate read-only ZCQL
              ↓
          Safety validation
              ↓
          KSP Data Store
          Gemini is therefore a bounded language capability, not the authority over the crime database.

Evidence and explainability

Vaani exposes the basis behind intelligence results through:

Data sources
Evidence basis
Method
Records considered
Limitations
Executed query where applicable

This allows investigators to understand where a result came from and how it was produced.

Authentication, RBAC and audit

Access to Vaani intelligence is protected through Zoho Catalyst Hosted Authentication.

The application uses role-based access with an Investigator role and records investigation activity through an audit trail.

Unauthenticated and unauthorized requests are rejected before protected intelligence is executed.

PDF case record

The active investigation conversation can be exported as a PDF for review and record keeping.

Architecture
                         Investigator
                    Voice / Text · English / Kannada
                                  |
                                  v
                    +---------------------------+
                    |      Vaani Frontend       |
                    |       HTML / CSS / JS     |
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    | Catalyst Authentication   |
                    | RBAC + Audit Controls      |
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    |   Conversation Context    |
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    |       Intent Router        |
                    +-------------+-------------+
                                  |
                     +------------+------------+
                     |                         |
                     v                         v
          +----------------------+   +----------------------+
          | Deterministic       |   | Open-ended Request  |
          | Intelligence        |   |                     |
          | Engines             |   |       Gemini        |
          +----------+-----------+   +----------+-----------+
                     |                          |
                     |                          v
                     |                  Candidate ZCQL
                     |                          |
                     |                  Safety Validation
                     |                          |
                     +------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    |    Catalyst Data Store    |
                    |      KSP Crime Data       |
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    | Evidence + Method         |
                    | Result + Context + Audit  |
                    +-------------+-------------+
                                  |
                                  v
                         Investigator
Core Design Principle

Vaani is not an LLM wrapped around a database.

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

For genuinely open-ended requests:

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

This gives Vaani conversational flexibility while keeping the core investigation workflow controlled, explainable and evidence-driven.

Key Differentiator

The conversation is the interface; evidence-backed intelligence is the foundation.

Vaani connects multiple investigative dimensions inside one conversation instead of treating FIR search, people, maps and analytics as separate tools.

An investigator can start with a case and progressively move toward:

Who → Where → What connects → What's missing → What should happen next

while preserving the active investigation context.

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
Authorization	Catalyst Role-Based Access
Audit	Application Audit Trail
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

The application is designed to fail closed for unauthenticated or unauthorized requests.

The Investigator role is intended for read-only access to KSP crime intelligence and investigation data.

Evidence & Safety

Vaani is designed as an investigative intelligence aid, not as a system that declares guilt.

For example, repeated appearance of a person across case records is treated as a relationship signal and not as proof of culpability.

Likewise, hotspot and proactive-signal outputs are presented as evidence-backed analytical indicators with their limitations shown to the investigator.

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

This demonstrates how Vaani moves from a single question to a deeper, evidence-backed investigation without switching between separate tools.

Local / Catalyst Deployment
Prerequisites
Node.js
Zoho Catalyst CLI
Catalyst account
Access to the required Catalyst project
Required environment variables for Gemini functionality when open-ended query generation is used
Prototype Scope

The prototype uses the available KSP reference crime dataset and focuses on a working conversational investigation workflow across the supported crime-intelligence paths.

The system is designed as decision support for investigators and does not replace formal police investigation procedures.

Team

Kusuma Uppalapati
Jahnavi Kesanapalli

Sri Vasavi Engineering College (SVEC), Tadepalligudem
