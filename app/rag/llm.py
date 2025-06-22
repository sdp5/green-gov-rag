from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from app.rag.vectorstore import load_vectorstore

def get_qa_chain():
    llm = OpenAI(temperature=0)
    vectorstore = load_vectorstore()
    retriever = vectorstore.as_retriever()
    chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
    return chain
