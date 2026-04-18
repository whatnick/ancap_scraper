"""Streamlit frontend for ANCAP Safety Q&A.

Talks to the FastAPI query-api service over HTTP.
Runs as an always-on K8s Deployment behind Cloudflare Tunnel.
"""

import os
import streamlit as st
import requests

API_URL = os.environ.get("QUERY_API_URL", "http://query-api:8000")

st.set_page_config(page_title="ANCAP Safety Q&A", page_icon="🚗", layout="centered")
st.title("ANCAP Vehicle Safety Q&A")
st.caption("Ask questions about vehicle safety ratings, features, and test results from ANCAP reports.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("Sources"):
                for s in msg["sources"]:
                    st.text(s)

if prompt := st.chat_input("e.g. Which vehicles got 5 stars in 2022?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching safety reports..."):
            try:
                resp = requests.post(
                    f"{API_URL}/query",
                    json={"question": prompt},
                    timeout=120,
                )
                resp.raise_for_status()
                data = resp.json()
                answer = data["answer"]
                sources = data.get("sources", [])
            except requests.exceptions.ConnectionError:
                answer = "Cannot reach the query API. Is the backend running?"
                sources = []
            except requests.exceptions.Timeout:
                answer = "The query timed out. Try a simpler question."
                sources = []
            except Exception as e:
                answer = f"Error: {e}"
                sources = []

        st.markdown(answer)
        if sources:
            with st.expander("Sources"):
                for s in sources:
                    st.text(s)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )

with st.sidebar:
    st.header("About")
    st.markdown(
        """
        This app uses **RAG** (Retrieval-Augmented Generation) to answer
        questions about vehicle safety data from
        [ANCAP](https://www.ancap.com.au).

        **Stack:**
        - Embeddings: Amazon Titan v2
        - LLM: Claude 3.5 Sonnet (Bedrock)
        - Vector Store: ChromaDB (local)
        - Framework: LangChain
        """
    )
    if st.button("Clear conversation"):
        st.session_state.messages = []
        try:
            requests.post(f"{API_URL}/reset", timeout=10)
        except Exception:
            pass
        st.rerun()
