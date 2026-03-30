# =============================================================================
# agent.py — LangChain ReAct Agent
# Architecture layer: Agent + LLM layer
# This is the brain of PharmOps AI Assistant.
# It receives a question, decides which tools to call (RAG and/or MCP),
# combines the results, and generates a sourced answer.
# ReAct pattern: Reason → Act → Observe → Reason → Answer
# =============================================================================

import os
import sys

# Add src directory to path so imports work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

# Import our two data layer modules
from rag_tool import search_sop_documents
from snowflake_tools import query_suppliers, query_open_pos

load_dotenv()


# =============================================================================
# Step 1 — Define the LLM
# gemini-2.0-flash — free tier, fast, strong reasoning for agent tasks
# temperature=0 means deterministic — same question gives consistent answer
# =============================================================================

llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-flash",
    temperature=0,
    max_tokens=2048
)


# =============================================================================
# Step 2 — Define the three tools
# Each Tool has a name, a function, and a description.
# The description is what the LLM reads to decide WHEN to call this tool.
# Write descriptions in clear business language — not technical language.
# =============================================================================

tools = [
    Tool(
        name="search_sop_documents",
        func=search_sop_documents,
        description=(
            "Search PharmaCo Standard Operating Procedure documents. "
            "Use this tool for questions about procedures, policies, or "
            "compliance requirements including: cold chain handling, "
            "temperature deviation procedures, GxP certification requirements, "
            "supplier qualification steps, CAPA procedures, quality hold "
            "procedures, deviation classification, supplier communication "
            "protocols, or site safety requirements. "
            "Input: a natural language question or topic."
        )
    ),
    Tool(
        name="get_supplier_info",
        func=lambda x: query_suppliers(
            site_code=x.strip() if "SITE" in x.upper() else None,
            gxp_expiring_days=90
        ),
        description=(
            "Query live supplier data from Snowflake. "
            "Use this tool for questions about: supplier GxP certification "
            "status or expiry, suspended suppliers, suppliers at a specific "
            "site, or suppliers with certification issues. "
            "Input: site code like 'SITE-A' or 'SITE-B', or 'ALL' for all sites."
        )
    ),
    Tool(
        name="get_open_purchase_orders",
        func=lambda x: query_open_pos(
            supplier_id=x.strip() if "SUP" in x.upper() else None,
            site_code=x.strip() if "SITE" in x.upper() else None
        ),
        description=(
            "Query live open purchase orders from Snowflake. "
            "Use this tool for questions about: open POs for a supplier, "
            "financial exposure on outstanding orders, POs at risk due to "
            "supplier issues, or open orders at a specific site. "
            "Input: supplier ID like 'SUP-005', or site code like 'SITE-A'."
        )
    )
]


# =============================================================================
# Step 3 — System prompt
# This tells the agent its role, what tools it has, and how to behave.
# Critically: it tells the agent to ALWAYS cite sources in its answer.
# =============================================================================

SYSTEM_PROMPT = """You are PharmOps AI Assistant — an intelligent assistant
for pharmaceutical manufacturing operations at PharmaCo.

You have access to three tools:
1. search_sop_documents — searches Standard Operating Procedure documents
2. get_supplier_info — queries live supplier data from Snowflake
3. get_open_purchase_orders — queries live open purchase orders from Snowflake

Your rules:
- Always use tools to find information before answering
- For procedure or policy questions — use search_sop_documents
- For supplier status or GxP questions — use get_supplier_info
- For purchase order questions — use get_open_purchase_orders
- For questions needing both document knowledge AND live data — use multiple tools
- Always cite your sources: name the SOP document or Snowflake table used
- If information is not found in tools, say so — do not guess
- Keep answers concise, factual, and actionable
- Format recommendations as numbered action steps when appropriate"""


# =============================================================================
# Step 4 — Create the ReAct agent using LangGraph
# create_react_agent wires the LLM and tools together into a reasoning loop
# =============================================================================

agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT
)


# =============================================================================
# Step 5 — run_agent function
# This is what app.py calls. Returns answer + list of tools used.
# =============================================================================

def run_agent(question: str) -> dict:
    """
    Run the ReAct agent on a question.
    Called by app.py for every user message in the Streamlit UI.

    Returns dict with:
        answer  — the final text answer from the agent
        sources — list of tool names that were called
    """
    print(f"\n[Agent] Processing: {question}")

    result = agent.invoke({
        "messages": [HumanMessage(content=question)]
    })

    # The last message in the result is the final answer
    messages = result["messages"]
    raw = messages[-1].content
    # Handle both string and list response formats from different Gemini models
    if isinstance(raw, list):
        final_answer = " ".join(
            part.get("text", "") for part in raw if isinstance(part, dict)
        )
    else:
        final_answer = raw

    # Collect which tools were called — used in the Sources panel in the UI
    sources = []
    for msg in messages:
        if hasattr(msg, 'name') and msg.name:
            sources.append(msg.name)

    # Remove duplicates while preserving order
    sources = list(dict.fromkeys(sources))

    return {
        "answer": final_answer,
        "sources": sources
    }


# =============================================================================
# Test block — run directly to test without the UI
# The Lonza question is the key demo moment — it needs both RAG and Snowflake
# =============================================================================

if __name__ == "__main__":
    print("=== PharmOps AI Assistant — Agent Test ===\n")

    # Test 1 — RAG only
    q1 = "What is the procedure for handling a cold chain temperature deviation?"
    print(f"Question 1: {q1}")
    print("-" * 60)
    result1 = run_agent(q1)
    print(f"\nAnswer:\n{result1['answer']}")
    print(f"\nSources used: {result1['sources']}")

    print("\n" + "=" * 60 + "\n")

    # Test 2 — THE LONZA DEMO QUESTION (RAG + Snowflake combined)
    q2 = ("Which suppliers at SITE-A have GxP certification issues "
          "and open purchase orders? What action should I take first?")
    print(f"Question 2 (Lonza demo): {q2}")
    print("-" * 60)
    result2 = run_agent(q2)
    print(f"\nAnswer:\n{result2['answer']}")
    print(f"\nSources used: {result2['sources']}")
