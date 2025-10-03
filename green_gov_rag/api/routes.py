"""API routes for GreenGovRAG."""

# Route handlers

from fastapi import APIRouter, Query

from green_gov_rag.rag.agent_tools import RAGAgent

router = APIRouter()
agent = RAGAgent()  # initialize with default vector store and embedder


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/query")
async def query_rag(
    q: str = Query(..., description="Query string"),
    jurisdiction: str | None = Query(None, description="Filter by jurisdiction"),
    category: str | None = Query(None, description="Filter by document category"),
    topic: str | None = Query(None, description="Filter by topic"),
    region: str | None = Query(None, description="Filter by region"),
):
    """Query RAG with optional metadata filters.
    Returns an answer + source documents.
    """
    metadata_filters = {}
    if jurisdiction:
        metadata_filters["jurisdiction"] = jurisdiction
    if category:
        metadata_filters["category"] = category
    if topic:
        metadata_filters["topic"] = topic
    if region:
        metadata_filters["region"] = region

    result = agent.query(text=q, metadata_filters=metadata_filters)
    return {"query": q, "filters": metadata_filters, "result": result}


@router.get("/documents")
async def list_documents():
    """List all ingested documents and their metadata."""
    docs = agent.list_documents()
    return {"documents": docs}
