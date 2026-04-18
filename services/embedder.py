"""Embedding pipeline: load PDFs, chunk, embed via Bedrock, store in ChromaDB.

Run as an Argo Workflow step or standalone:
    python embedder.py --pdf-dir /data/pdfs --chroma-dir /data/chromadb
"""

import os
import argparse

from langchain_aws import BedrockEmbeddings
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter


def embed_pdfs(pdf_dir: str, chroma_dir: str, chroma_host: str, chroma_port: int):
    print(f"Loading PDFs from {pdf_dir}")
    loader = PyPDFDirectoryLoader(pdf_dir)
    docs = loader.load()
    print(f"Loaded {len(docs)} pages from PDFs")

    if not docs:
        print("No documents found. Exiting.")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks")

    region = os.environ.get("BEDROCK_REGION", "us-east-1")
    model_id = os.environ.get("EMBED_MODEL", "amazon.titan-embed-text-v2:0")

    embeddings = BedrockEmbeddings(
        model_id=model_id,
        region_name=region,
    )

    if chroma_host:
        import chromadb
        client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        vectordb = Chroma.from_documents(
            chunks,
            embedding=embeddings,
            client=client,
            collection_name="ancap_safety",
        )
    else:
        vectordb = Chroma.from_documents(
            chunks,
            embedding=embeddings,
            persist_directory=chroma_dir,
            collection_name="ancap_safety",
        )

    print(f"Indexed {len(chunks)} chunks into ChromaDB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed ANCAP PDFs into ChromaDB")
    parser.add_argument("--pdf-dir", default=os.environ.get("PDF_DIR", "/data/pdfs"))
    parser.add_argument("--chroma-dir", default=os.environ.get("CHROMA_DIR", "/data/chromadb"))
    parser.add_argument("--chroma-host", default=os.environ.get("CHROMA_HOST", ""))
    parser.add_argument("--chroma-port", type=int, default=int(os.environ.get("CHROMA_PORT", "8000")))
    args = parser.parse_args()
    embed_pdfs(args.pdf_dir, args.chroma_dir, args.chroma_host, args.chroma_port)
