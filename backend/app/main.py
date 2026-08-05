from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routes.health import router as health_router
from app.api.routes.vector_retrieval import router as vector_retrieval_router

app = FastAPI(title="EconomyMate API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_INDEX = Path(__file__).parent / "static" / "index.html"


@app.get("/", response_class=FileResponse)
@app.get("/be2-demo", response_class=FileResponse)
def get_demo_page():
    return FileResponse(STATIC_INDEX)


app.include_router(health_router)
app.include_router(vector_retrieval_router)
