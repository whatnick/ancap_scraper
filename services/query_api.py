"""FastAPI service for semantic Q&A over ANCAP safety data.

Connects to local ChromaDB for retrieval and AWS Bedrock for
LLM inference + embeddings. Runs as an always-on K8s Deployment.
"""

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from langchain_aws import BedrockEmbeddings, ChatBedrock
from langchain_community.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

CHROMA_DIR = os.environ.get("CHROMA_DIR", "/data/chromadb")
CHROMA_HOST = os.environ.get("CHROMA_HOST", "")  # empty = local persistent dir
CHROMA_PORT = int(os.environ.get("CHROMA_PORT", "8000"))
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "amazon.titan-embed-text-v2:0")
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
RETRIEVER_K = int(os.environ.get("RETRIEVER_K", "4"))

qa_chain = None
memory = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global qa_chain, memory

    embeddings = BedrockEmbeddings(
        model_id=EMBED_MODEL,
        region_name=BEDROCK_REGION,
    )

    if CHROMA_HOST:
        import chromadb
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        vectordb = Chroma(
            client=client,
            collection_name="ancap_safety",
            embedding_function=embeddings,
        )
    else:
        vectordb = Chroma(
            persist_directory=CHROMA_DIR,
            collection_name="ancap_safety",
            embedding_function=embeddings,
        )

    llm = ChatBedrock(
        model_id=LLM_MODEL,
        model_kwargs={"temperature": LLM_TEMPERATURE, "max_tokens": 2048},
        region_name=BEDROCK_REGION,
    )

    memory = ConversationBufferMemory(
        memory_key="chat_history", return_messages=True
    )

    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectordb.as_retriever(search_kwargs={"k": RETRIEVER_K}),
        memory=memory,
        return_source_documents=True,
    )

    yield


app = FastAPI(title="ANCAP Safety Q&A", lifespan=lifespan)


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]


class HealthResponse(BaseModel):
    status: str
    vector_store: str


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        vector_store="chroma",
    )


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if qa_chain is None:
        raise HTTPException(status_code=503, detail="QA chain not initialized")

    result = qa_chain({"question": req.question})
    sources = []
    for doc in result.get("source_documents", []):
        src = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        sources.append(f"{src} (page {page})")

    return QueryResponse(answer=result["answer"], sources=list(set(sources)))


@app.post("/reset")
async def reset_memory():
    if memory is not None:
        memory.clear()
    return {"status": "memory cleared"}
