# API endpoints

from fastapi import FastAPI
from api.routes import router as api_router

app = FastAPI(
    title="GreenGovRAG API",
    description="API for querying environmental regulations with RAG + geospatial filters",
    version="0.1"
)

app.include_router(api_router)
