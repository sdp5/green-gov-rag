from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.rag.vectorstore import save_vectorstore
import os

def load_pdfs(directory="data/raw_docs"):
    all_docs = []
    for file in os.listdir(directory):
        if file.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(directory, file))
            all_docs.extend(loader.load())
    return all_docs

def split_documents(docs):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return splitter.split_documents(docs)

if __name__ == "__main__":
    print("Ingesting documents...")
    docs = load_pdfs()
    chunks = split_documents(docs)
    save_vectorstore(chunks)
    print(f"Ingested {len(chunks)} chunks.")
