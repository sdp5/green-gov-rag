# Embedding setup (OpenAI, HF)

from langchain.embeddings import OpenAIEmbeddings


def get_embedding_model():
    return OpenAIEmbeddings()
