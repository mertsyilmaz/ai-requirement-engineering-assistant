from fastapi import FastAPI

from app.api.analysis_controller import router as analysis_router

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Backend is running"}


app.include_router(analysis_router)