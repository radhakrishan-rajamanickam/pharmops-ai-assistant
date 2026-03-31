# PharmOps AI Assistant

**A personal architecture POC demonstrating LLM + RAG + MCP + Agent for pharmaceutical supply chain operations intelligence.**

Built by Radhakrishnan Rajamanickam — Senior Data & AI Architect  
Personal exploration of agentic AI architecture patterns applicable to regulated pharma manufacturing environments.

---

## Table of Contents

- [What this does](#what-this-does)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup from scratch](#setup-from-scratch)
- [Running the scripts — step by step](#running-the-scripts--step-by-step)
- [The demo question](#the-demo-question)
- [JD mapping](#jd-mapping)
- [Production considerations](#production-considerations)
- [Troubleshooting](#troubleshooting)

---

## What this does

Operations managers in pharma manufacturing need to cross-reference three systems to answer one question:

- **SOP documents** — procedures, policies, deviation handling
- **Live supplier data** — GxP certification status, expiry dates
- **Live procurement data** — open purchase orders, financial exposure

This assistant answers natural-language questions by combining all three sources in under 10 seconds.

**The Lonza AG demo scenario:**  
Question: *"Which SITE-A suppliers have GxP certification issues and open purchase orders? What action should I take first?"*

Answer: Lonza AG (SUP-005) has a lapsed GxP certificate (expired 2026-02-01) and is SUSPENDED. Open PO-2026-005 is worth $89,500. Per SOP-SC-0018 and SOP-OPS-0007: place PO on Quality Hold immediately, notify Operations Manager within 4 hours, initiate CAPA within 5 business days.

That answer combines live Snowflake data with SOP document knowledge — neither source alone produces it.

---

## Architecture

```
User (Streamlit UI)
        │
        ▼
    app.py  ──────────────────────────────── Streamlit Cloud (public URL)
        │
        ▼
    agent.py  ── LangChain ReAct Agent (Gemini 2.5 Flash)
        │
        ├──── search_sop_documents()  ──────── rag_tool.py
        │              │
        │              ▼
        │         FAISS vector index  ──── data/faiss_index/
        │              │
        │              ▼
        │         docs/ (5 SOP .txt files)
        │
        ├──── get_supplier_info()  ─────────── mcp_server.py
        │              │
        └──── get_open_purchase_orders()       snowflake_tools.py
                       │
                       ▼
                  Snowflake PHARMOPS_DEMO
                  (DIM_SUPPLIER · FACT_OPEN_POS)
```

**Five layers:**

| Layer | File | What it does |
|---|---|---|
| UI | `src/app.py` | Streamlit chat interface with sources panel |
| Agent | `src/agent.py` | LangChain ReAct agent — decides which tools to call |
| RAG tool | `src/rag_tool.py` | Semantic search over SOP documents via FAISS |
| MCP tools | `src/mcp_server.py` | Exposes Snowflake queries as MCP-compatible tools |
| Data layer | `src/snowflake_tools.py` | Raw Snowflake SQL queries |
| Build script | `src/ingest.py` | One-time: chunks SOPs, embeds, builds FAISS index |

---

## Project structure

```
pharmops-ai-assistant/
│
├── docs/                               ← 5 SOP text files (RAG knowledge base)
│   ├── SOP-QA-0042-cold-chain.txt
│   ├── SOP-SC-0018-supplier-qualification.txt
│   ├── SOP-SC-0031-po-deviation.txt
│   ├── SOP-QA-0015-site-safety.txt
│   └── SOP-OPS-0007-supplier-communication.txt
│
├── src/                                ← all Python source files
│   ├── ingest.py                       ← RUN ONCE: builds FAISS index from SOPs
│   ├── rag_tool.py                     ← search_sop_documents() function
│   ├── snowflake_tools.py              ← query_suppliers() + query_open_pos()
│   ├── mcp_server.py                   ← MCP server exposing Snowflake tools
│   ├── agent.py                        ← LangChain ReAct agent (main brain)
│   ├── app.py                          ← Streamlit UI
│   └── test_faiss.py                   ← optional: test FAISS retrieval directly
│
├── data/
│   └── faiss_index/                    ← built by ingest.py, committed to GitHub
│       ├── index.faiss                 ← vector index (50 chunks)
│       └── index.pkl                   ← metadata (source filenames)
│
├── snowflake_setup.sql                 ← SQL to create Snowflake tables + data
├── .env                                ← YOUR secrets — never committed to GitHub
├── .env.example                        ← template showing required variables
├── requirements.txt                    ← direct Python dependencies
├── .gitignore
└── README.md
```

---

## Prerequisites

- Python 3.9 or above (tested on 3.10.11)
- Git
- VS Code (recommended)
- A Google Gemini API key (free — aistudio.google.com)
- A Snowflake account (free 30-day trial — trial.snowflake.com)

---

## Setup from scratch

These steps assume you are starting on a fresh machine. If you already
have the project cloned and running, skip to
[Running the scripts](#running-the-scripts--step-by-step).

### Step 1 — Clone the repo

```
git clone https://github.com/saror-pensieve/pharmops-ai-assistant.git
cd pharmops-ai-assistant
```

### Step 2 — Create and activate virtual environment

Windows (Command Prompt — not PowerShell):
```
python -m venv venv
venv\Scripts\activate.bat
```

Mac/Linux:
```
python -m venv venv
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt.

### Step 3 — Install packages

```
pip install -r requirements.txt
```

This installs: langchain, langchain-google-genai, langchain-community,
langchain-text-splitters, faiss-cpu, streamlit, snowflake-connector-python,
python-dotenv, mcp, and google-genai.

Verify everything installed:
```
python -c "import langchain; import faiss; import streamlit; import snowflake.connector; print('All packages OK')"
```

### Step 4 — Create your .env file

Create a file called `.env` in the project root (same level as README.md).
Copy the contents of `.env.example` and fill in your real values:

```
GOOGLE_API_KEY=AIzaSy...your_39_char_key_here

SNOWFLAKE_ACCOUNT=ORGNAME-ACCOUNTNAME
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=PHARMOPS_DEMO
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
```

**Where to get the Gemini API key:**  
Go to aistudio.google.com → sign in → Get API key → Create API key.
The key starts with `AIzaSy` and is 39 characters long.

**Where to get the Snowflake account identifier:**  
Sign in to Snowflake → look at the bottom-left of the screen → hover over
your account name → copy the Account Identifier. Format: `ORGNAME-ACCOUNTNAME`.

**Verify credentials are readable:**
```
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Gemini:', os.getenv('GOOGLE_API_KEY')[:8]); print('Snowflake:', os.getenv('SNOWFLAKE_ACCOUNT'))"
```

### Step 5 — Set up Snowflake database

Open `snowflake_setup.sql` in your Snowflake worksheet (Projects → Worksheets).
Select all and run. This creates:
- Database: `PHARMOPS_DEMO`
- Tables: `DIM_SUPPLIER` (8 rows) and `FACT_OPEN_POS` (12 rows)
- Sample data including the Lonza AG demo scenario

Verify by running in Snowflake:
```sql
SELECT COUNT(*) FROM PHARMOPS_DEMO.PUBLIC.DIM_SUPPLIER;    -- should return 8
SELECT COUNT(*) FROM PHARMOPS_DEMO.PUBLIC.FACT_OPEN_POS;   -- should return 12
```

---

## Running the scripts — step by step

Always make sure `(venv)` is active before running any script.
All commands run from the **project root** (where README.md lives).

---

### Script 1: ingest.py — build the FAISS index

**Run this once. Only re-run if you change or add SOP documents.**

```
python src/ingest.py
```

**What it does:**
1. Loads all 5 `.txt` files from `docs/`
2. Splits each into chunks (500 chars, 50-char overlap)
3. Sends each chunk to Gemini embedding API (`gemini-embedding-001`)
4. Stores all 50 vectors in a FAISS index
5. Saves `data/faiss_index/index.faiss` and `data/faiss_index/index.pkl`

**Expected output:**
```
=== PharmOps RAG Ingestion Pipeline ===

[1/3] Loading SOP documents from docs/ folder...
  Loaded: SOP-OPS-0007-supplier-communication.txt
  Loaded: SOP-QA-0015-site-safety.txt
  Loaded: SOP-QA-0042-cold-chain.txt
  Loaded: SOP-SC-0018-supplier-qualification.txt
  Loaded: SOP-SC-0031-po-deviation.txt
  Documents loaded: 5

[2/3] Splitting documents into chunks...
  Total chunks created: 50

[3/3] Building FAISS vector index...
  Creating embeddings — calling Gemini API, may take 30 seconds...
  FAISS index saved to: data/faiss_index

=== Ingestion complete. FAISS index is ready. ===
```

**If it fails:**  
- `API key not valid` — check your GOOGLE_API_KEY in `.env`. Must be 39 chars starting with `AIzaSy`.
- `model not found` — the confirmed working embedding model is `models/gemini-embedding-001`. Check `src/ingest.py` line with `model=`.
- `No module named langchain_text_splitters` — run `pip install langchain-text-splitters`.

---

### Script 2: rag_tool.py — test RAG retrieval

**Run this to verify the FAISS index works before testing the full agent.**

```
python src/rag_tool.py
```

**What it does:**  
Loads the FAISS index and runs two test queries. Returns the top-3 most
semantically similar SOP chunks for each question.

**Expected output (abbreviated):**
```
Loading FAISS index...
FAISS index loaded — RAG tool ready.

=== RAG Tool Test ===

Question: What is the procedure for handling a cold chain temperature deviation?
------------------------------------------------------------
[Source 1: SOP-QA-0042-cold-chain.txt]
6. RESPONSE PROCEDURE FOR TEMPERATURE DEVIATION
Step 1: Upon detection of deviation...

---

[Source 2: SOP-QA-0042-cold-chain.txt]
5. DEVIATION DETECTION AND CLASSIFICATION
5.1 Minor deviation...

---

[Source 3: SOP-OPS-0007-supplier-communication.txt]
Scenario B — Cold chain deviation, supplier materials affected...
```

**What good looks like:**  
Question 1 retrieves chunks from `SOP-QA-0042-cold-chain.txt`.  
Question 2 retrieves chunks from `SOP-SC-0018-supplier-qualification.txt`.  
Source 3 often comes from a different SOP — this is semantic search working
correctly (finds related content even from a different document).

---

### Script 3: snowflake_tools.py — test live Snowflake queries

**Run this to verify Snowflake connection and queries before testing the agent.**

```
python src/snowflake_tools.py
```

**What it does:**  
Runs 4 test queries against Snowflake:
- Test 1: All SITE-A suppliers
- Test 2: Suppliers with GxP expiring within 90 days (Lonza AG appears here)
- Test 3: Open POs for Lonza AG (SUP-005)
- Test 4: All open POs at SITE-A

**Expected output for Test 2 (the key scenario):**
```
[Test 2] Suppliers with GxP expiring within 90 days:
SUPPLIER QUERY RESULTS:
--------------------------------------------------
Supplier ID:    SUP-005
Name:           Lonza AG
Site:           SITE-A
GxP Certified:  False
GxP Expiry:     2026-02-01
Status:         SUSPENDED
--------------------------------------------------
```

**If it fails:**  
- `Incorrect username or password` — check SNOWFLAKE_USER and SNOWFLAKE_PASSWORD in `.env`.
- `Account identifier` error — check SNOWFLAKE_ACCOUNT format. Should be `ORGNAME-ACCOUNTNAME` with no `.snowflakecomputing.com`.
- `pyarrow` warning — this is harmless. The app works correctly despite this warning.

---

### Script 4: mcp_server.py — start the MCP server

**Run this to verify the MCP server starts correctly.**  
Note: in the full app, the agent imports the Snowflake functions directly.
This script is for testing the MCP server in isolation.

```
cd src
python mcp_server.py
```

**Expected output:**
```
=== PharmOps MCP Server starting ===
Tools available:
  - get_supplier_info
  - get_open_purchase_orders
Server running — waiting for agent connections...
```

The server waits — this is correct. Press `Ctrl + C` to stop it.  
Then return to project root:
```
cd ..
```

---

### Script 5: agent.py — test the full agent

**Run this to test the complete agent without the UI.**  
This is the key test — the Lonza scenario should produce a combined answer.

```
python src/agent.py
```

**What it does:**  
Runs two test questions through the full ReAct agent loop:
- Question 1: Cold chain procedure (RAG only — tests document retrieval)
- Question 2: Lonza demo scenario (RAG + MCP — tests combined reasoning)

**Expected output for Question 2 (the showstopper):**
```
[Agent] Processing: Which suppliers at SITE-A have GxP certification issues
and open purchase orders? What action should I take first?

Answer:
Supplier SUP-005 (Lonza AG) at SITE-A has GxP certification issues
(GxP Certified: False) and is currently SUSPENDED.
There is an open purchase order PO-2026-005 worth $89,500.00.

Action to take first:
1. Place PO-2026-005 on Quality Hold immediately
2. Call Lonza AG Quality Director
3. Send formal suspension notice within 2 hours
4. Notify site Operations Manager within 4 hours
5. Initiate CAPA within 5 business days

Sources used: ['get_supplier_info', 'get_open_purchase_orders']
```

**Important — API rate limits:**  
The Gemini free tier allows 20 requests per day and 5 per minute for
`gemini-2.5-flash`. Each complex question uses 3-4 requests (one per
ReAct loop iteration). If you see `429 RESOURCE_EXHAUSTED`:
- Wait 60 seconds and retry (per-minute limit)
- Or wait until midnight Pacific time (resets daily quota)
- The confirmed working model is `models/gemini-2.5-flash`

**If the model is not found:**  
Run this to list available models on your API key:
```
python -c "from dotenv import load_dotenv; import os; load_dotenv(); from google import genai; client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY')); [print(m.name) for m in client.models.list() if 'generateContent' in (m.supported_actions or [])]"
```

---

### Script 6: app.py — run the Streamlit UI

**Run this to start the full chat interface locally.**

```
streamlit run src/app.py
```

Your browser opens automatically at `http://localhost:8501`.

**What you see:**
- Left sidebar with project description, architecture summary, and 3 demo questions
- Chat input box at the bottom
- AI responses with a collapsible "Sources used" panel showing which tools were called

**To stop the app:**  
Press `Ctrl + C` in the terminal.

**Three demo questions to run (in this order to manage API quota):**

1. `What is the cold chain deviation procedure?`  
   Uses 2 API calls. Tests RAG only. Should return SOP-QA-0042 content.

2. `Which SITE-A suppliers have GxP certs expiring within 90 days?`  
   Uses 2 API calls. Tests MCP only. Should return Lonza AG.

3. `Which suppliers at SITE-A have GxP certification issues and open POs? What action should I take first?`  
   Uses 3-4 API calls. Tests both RAG + MCP combined. The showstopper demo.

---

## The demo question

This is the question to ask in any live demo:

> *"Which suppliers at SITE-A have GxP certification issues and open purchase orders? What action should I take first?"*

**Why this question works:**  
It requires the agent to call three tools in sequence — `get_supplier_info` to find Lonza AG suspended, `get_open_purchase_orders` to find the $89,500 open PO, and `search_sop_documents` to retrieve the action procedure from SOP-SC-0018. No single tool produces a complete answer. Only the agent combining all three does.

**What to say while it runs:**  
*"The agent is now deciding which tools to call. It will query live Snowflake data for supplier status and open POs, then search the SOP knowledge base for the required action procedure. Watch the Sources panel — it will show exactly which systems contributed to this answer."*

---

## Skill mapping

| Skill requirement | POC implementation | File |
|---|---|---|
| LangChain orchestration | ReAct agent with create_react_agent | src/agent.py |
| RAG + semantic search | FAISS + Gemini embeddings | src/rag_tool.py, src/ingest.py |
| Vector databases | FAISS (→ Pinecone for production) | data/faiss_index/ |
| Model Context Protocol | FastMCP server with two tools | src/mcp_server.py |
| Python throughout | All backend in Python | src/*.py |
| Snowflake + SQL | Live queries with dynamic WHERE | src/snowflake_tools.py |
| AI Governance | RAG filters ACTIVE SOPs only | src/rag_tool.py |
| Hallucination mitigation | System prompt citation enforcement | src/agent.py |
| FinOps for AI | Gemini free tier · documented model selection | src/agent.py |
| Agentic workflows | Multi-tool ReAct loop | src/agent.py |

---

## Production considerations

What I would do differently at Compay scale:

**1 — Replace FAISS with Pinecone or Snowflake Cortex**  
FAISS is file-based and single-node. At AZ scale with thousands of SOPs
across 50 sites, a managed vector database handles millions of vectors,
metadata filtering, and concurrent queries without infrastructure management.
The LangChain abstraction means the code change is minimal.

**2 — Add governance filter at retrieval time**  
In production, SOPs exist in DRAFT, ACTIVE, SUPERSEDED, and ARCHIVED states.
The RAG retrieval must filter to ACTIVE documents only — that approved status
comes from Collibra. Without this filter, the agent could retrieve a
superseded SOP and give outdated guidance to an operations manager.

**3 — Event-driven ingestion pipeline**  
Replace the manual `ingest.py` script with an event-driven pipeline —
AWS Lambda triggered by a Collibra SOP approval workflow. New documents
become searchable within minutes of approval, not days.

**4 — Chunk-level provenance**  
Each retrieved chunk must carry its Collibra asset ID, version number,
approval date, and steward name — not just the filename. Every AI answer
becomes auditable back to the approved governance record.

**5 — Azure OpenAI for production LLM**  
Replace Gemini with Azure OpenAI GPT-4o. AZ's primary cloud is Azure,
data residency requirements are met, and the enterprise agreement covers
the data processing terms required for pharmaceutical-grade compliance.

**6 — React TypeScript front end**  
Replace Streamlit with a React TypeScript application. Streamlit is the
right choice for a 3-day prototype. Production requires proper state
management, authentication integration, and mobile responsiveness.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `venv\Scripts\activate` fails in PowerShell | PowerShell execution policy | Use Command Prompt, not PowerShell. Or run `Set-ExecutionPolicy RemoteSigned` |
| `All packages OK` but pyarrow warning | pyarrow version mismatch with Snowflake | Harmless — ignore. App works correctly |
| `API key not valid` | Wrong or truncated Gemini key | Key must be exactly 39 chars starting with `AIzaSy`. Check `.env` for extra spaces or quotes |
| `models/text-embedding-004 not found` | Wrong embedding model name | Use `models/gemini-embedding-001` — confirmed working on free tier |
| `429 RESOURCE_EXHAUSTED` | Gemini free tier rate limit hit | Wait 60 seconds (per-minute limit) or until midnight Pacific (daily limit). Free tier: 20 requests/day for gemini-2.5-flash |
| `Incorrect username or password` Snowflake | Wrong credentials in `.env` | Check SNOWFLAKE_USER and SNOWFLAKE_PASSWORD. Account identifier format: `ORGNAME-ACCOUNTNAME` |
| `cannot import name Tool from langchain.tools` | LangChain version changed import path | Use `from langchain_core.tools import Tool` |
| `ModuleNotFoundError: langchain.text_splitter` | LangChain version changed import path | Use `from langchain_text_splitters import RecursiveCharacterTextSplitter` |
| Agent answer wrapped in `[{'type': 'text', ...}]` | Gemini 2.5 Flash returns structured content blocks | Already handled in `run_agent()` — checks `isinstance(raw, list)` and extracts text |

---

## Running order summary

```
First time only:
  1. python src/ingest.py          ← builds FAISS index from SOPs

Every session:
  2. python src/rag_tool.py        ← verify RAG works (optional)
  3. python src/snowflake_tools.py ← verify Snowflake works (optional)
  4. python src/agent.py           ← test full agent in terminal (optional)
  5. streamlit run src/app.py      ← launch the chat UI
```

Steps 2, 3, and 4 are optional verification steps. If the app worked
yesterday and you have not changed any code, skip straight to step 5.

---

*Built by Radhakrishnan Rajamanickam — personal POC for AI architecture exploration.*  
*Not  IP — generic pharma operations domain, fictional company and site names.*
