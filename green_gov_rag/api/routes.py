# Route handlers

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/query")
def query_policy(question: str):
    # TODO: Call RAG system
    return {"answer": f"Response to '{question}' (stub)"}
