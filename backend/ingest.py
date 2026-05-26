"""
MathTales AI – Knowledge ingestion for RAG
Builds the FAISS vector store from:
  1. Structured Grade 1–6 knowledge (knowledge/*.md)
  2. Optional PDF (e.g. Story-Based_Mathematics_Grades_1-6.pdf)

Run from backend directory:
  python ingest.py              # ingest knowledge/ + PDF if present
  python ingest.py --knowledge-only   # only knowledge/*.md
  python ingest.py --pdf-only        # only PDF
"""

import os
import argparse
from pathlib import Path

# from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
import pickle

# load_dotenv()

TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    is_separator_regex=False,
)


def ingest_documents(documents: list, vectorstore_path: str) -> None:
    if not documents:
        print("No documents to ingest.")
        return
    print(f"Splitting {len(documents)} document(s) into chunks...")
    chunks = TEXT_SPLITTER.split_documents(documents)
    
    print(f"Creating vector store for {len(chunks)} chunks (BAAI/bge-small-en-v1.5)...")
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    print(f"Saving vector store to {vectorstore_path}...")
    vectorstore.save_local(vectorstore_path)
    
    print("Creating BM25 keyword index...")
    bm25_retriever = BM25Retriever.from_documents(chunks)
    bm25_path = f"{vectorstore_path}_bm25.pkl"
    with open(bm25_path, "wb") as f:
        pickle.dump(bm25_retriever, f)
    print(f"Saved BM25 retriever to {bm25_path}")
    
    print("Ingestion complete.")


def load_pdf(pdf_path: str) -> list:
    print(f"Loading PDF: {pdf_path}...")
    loader = PyPDFLoader(pdf_path)
    return loader.load()


def load_knowledge_dir(knowledge_dir: str) -> list:
    """Load all .md and .txt files from knowledge/ (Grade 1–6 curated content)."""
    path = Path(knowledge_dir)
    if not path.is_dir():
        return []
    docs = []
    for ext in ("*.md", "*.txt"):
        for f in path.glob(ext):
            try:
                loader = TextLoader(str(f), encoding="utf-8")
                docs.extend(loader.load())
            except Exception as e:
                print(f"  Skip {f}: {e}")
    print(f"Loaded {len(docs)} file(s) from {knowledge_dir}.")
    return docs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest knowledge for MathTales RAG")
    parser.add_argument("--knowledge-only", action="store_true", help="Only ingest knowledge/*.md")
    parser.add_argument("--pdf-only", action="store_true", help="Only ingest PDF")
    parser.add_argument("--pdf", default="Story-Based_Mathematics_Grades_1-6.pdf", help="PDF path")
    parser.add_argument("--knowledge", default="knowledge", help="Knowledge directory")
    parser.add_argument("--output", default="vectorstore", help="Output vector store path")
    args = parser.parse_args()

    all_docs = []

    if not args.pdf_only:
        knowledge_docs = load_knowledge_dir(args.knowledge)
        all_docs.extend(knowledge_docs)

    if not args.knowledge_only and os.path.exists(args.pdf):
        pdf_docs = load_pdf(args.pdf)
        all_docs.extend(pdf_docs)
    elif not args.knowledge_only:
        print(f"PDF not found: {args.pdf} (skipped)")

    ingest_documents(all_docs, args.output)
