# API endpoints

from fastapi import FastAPI
from api.routes import router

app = FastAPI(title="GreenGovRAG API")

app.include_router(router)

@app.get("/")
def root():
    return {"message": "GreenGovRAG API is running"}
