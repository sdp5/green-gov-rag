# FAISS/Qdrant setup

from langchain.vectorstores import FAISS


def load_vectorstore(index_path):
    return FAISS.load_local(index_path)
