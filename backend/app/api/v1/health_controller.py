from fastapi import APIRouter


router = APIRouter(prefix="/api/v1/health", tags=["Health"])


@router.get("")
#---------- <Summary> ----------
# Summary: Returns a lightweight API health response.
#---------- </Summary> ----------
def health_check():
    return {
        "status": "ok",
        "message": "API is running",
    }
