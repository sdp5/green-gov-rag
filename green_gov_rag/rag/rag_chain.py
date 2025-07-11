# LangChain RAG chain logic

from langchain.chains import RetrievalQA
from langchain.llms import OpenAI


def create_rag_chain(retriever):
    llm = OpenAI(temperature=0)
    return RetrievalQA(llm=llm, retriever=retriever)
