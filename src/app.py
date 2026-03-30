# =============================================================================
# app.py — Streamlit Chat Interface
# Architecture layer: UI layer
# This is the front end of PharmOps AI Assistant.
# It provides a chat interface that calls the agent and displays answers
# with a sources panel showing which tools were used.
# Run: streamlit run src/app.py
# =============================================================================

import sys
import os

# Add src directory to path so agent.py can find its imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from agent import run_agent

# =============================================================================
# Page configuration — sets browser tab title and layout
# =============================================================================

st.set_page_config(
    page_title="PharmOps AI Assistant",
    page_icon="💊",
    layout="wide"
)

# =============================================================================
# Sidebar — project information and tech stack
# =============================================================================

with st.sidebar:
    st.title("💊 PharmOps AI")
    st.markdown("---")

    st.markdown("### About")
    st.markdown(
        "A personal POC demonstrating LLM + RAG + MCP + Agent "
        "architecture for pharmaceutical supply chain operations intelligence."
    )

    st.markdown("---")
    st.markdown("### Architecture")
    st.markdown("""
    - 🧠 **Agent**: LangChain ReAct + Gemini
    - 📄 **RAG**: FAISS vector store + SOP docs
    - 🔌 **MCP**: Snowflake live data tools
    - 💬 **UI**: Streamlit
    """)

    st.markdown("---")
    st.markdown("### Demo questions")
    st.markdown("""
    Try asking:
    1. *What is the cold chain deviation procedure?*
    2. *Which SITE-A suppliers have GxP issues?*
    3. *Which suppliers have open POs and certification problems?*
    """)

    st.markdown("---")
    st.markdown("### Built by")
    st.markdown("Radhakrishnan Rajamanickam")
    st.markdown("Senior Data & AI Architect")
    st.markdown(
        "[![GitHub](https://img.shields.io/badge/GitHub-pharmops--ai--assistant-blue)]"
        "(https://github.com/saror-pensieve/pharmops-ai-assistant)"
    )

# =============================================================================
# Main chat interface
# =============================================================================

st.title("PharmOps AI Assistant")
st.markdown(
    "Ask any question about pharmaceutical operations — "
    "procedures, supplier status, purchase orders, or compliance."
)

# Initialise chat history in session state
# Session state persists across reruns within the same browser session
if "messages" not in st.session_state:
    st.session_state.messages = []

if "sources_history" not in st.session_state:
    st.session_state.sources_history = []

# Display existing chat history
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Show sources expander for assistant messages
        if message["role"] == "assistant" and i // 2 < len(st.session_state.sources_history):
            sources = st.session_state.sources_history[i // 2]
            if sources:
                with st.expander("📚 Sources used"):
                    for source in sources:
                        if source == "search_sop_documents":
                            st.markdown("📄 **RAG** — SOP document knowledge base (FAISS)")
                        elif source == "get_supplier_info":
                            st.markdown("🗄️ **MCP** — Snowflake `DIM_SUPPLIER` table")
                        elif source == "get_open_purchase_orders":
                            st.markdown("🗄️ **MCP** — Snowflake `FACT_OPEN_POS` table")
                        else:
                            st.markdown(f"🔧 {source}")

# Chat input box — appears at the bottom of the page
if prompt := st.chat_input("Ask about pharma operations..."):

    # Add user message to chat history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call the agent and display the response
    with st.chat_message("assistant"):
        with st.spinner("Thinking — searching SOPs and querying live data..."):
            try:
                result = run_agent(prompt)
                answer = result["answer"]
                sources = result["sources"]

            except Exception as e:
                answer = (
                    f"I encountered an error: {str(e)}\n\n"
                    "This may be due to API rate limits. "
                    "Please wait 60 seconds and try again."
                )
                sources = []

        # Display the answer
        st.markdown(answer)

        # Display sources expander
        if sources:
            with st.expander("📚 Sources used"):
                for source in sources:
                    if source == "search_sop_documents":
                        st.markdown("📄 **RAG** — SOP document knowledge base (FAISS)")
                    elif source == "get_supplier_info":
                        st.markdown("🗄️ **MCP** — Snowflake `DIM_SUPPLIER` table")
                    elif source == "get_open_purchase_orders":
                        st.markdown("🗄️ **MCP** — Snowflake `FACT_OPEN_POS` table")
                    else:
                        st.markdown(f"🔧 {source}")

    # Save to history
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.sources_history.append(sources)
