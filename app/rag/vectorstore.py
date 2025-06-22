import os
import faiss
import pickle
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings

def get_vectorstore_path():
    return "data/processed_docs/faiss_index"

def load_vectorstore():
    embedding = OpenAIEmbeddings()
    path = get_vectorstore_path()
    return FAISS.load_local(path, embeddings=embedding)

def save_vectorstore(documents):
    embedding = OpenAIEmbeddings()
    db = FAISS.from_documents(documents, embedding)
    db.save_local(get_vectorstore_path())
    return db
