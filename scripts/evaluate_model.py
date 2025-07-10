from rag.rag_chain import create_rag_chain
from rag.vector_store import load_vectorstore

EXAMPLES = [
    "What are the native vegetation clearance rules in SA?",
    "Do I need an EIS for a wind farm in NSW?",
    "What are emissions standards in Victoria?"
]

def evaluate():
    retriever = load_vectorstore("data/processed/default").as_retriever()
    rag_chain = create_rag_chain(retriever)

    for query in EXAMPLES:
        print(f"\n🔍 Query: {query}")
        result = rag_chain.run(query)
        print(f"🧠 Answer: {result}")

if __name__ == "__main__":
    evaluate()
