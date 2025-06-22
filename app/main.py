from fastapi import FastAPI
from app.api.routes import router as api_router

app = FastAPI(
    title="GreenGovRAG",
    description="RAG-based GenAI assistant for navigating environmental policies in Australia",
    version="0.1.0"
)

app.include_router(api_router, prefix="/api")
