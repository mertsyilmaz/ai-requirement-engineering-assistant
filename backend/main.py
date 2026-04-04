from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.core.logging_config import setup_logging

setup_logging()

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Backend is running"}


app.include_router(v1_router)