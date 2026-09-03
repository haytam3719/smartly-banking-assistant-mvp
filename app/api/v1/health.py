from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> dict[str, str]:
    # In a hardened deployment, check required downstreams with tight time budgets.
    return {"status": "ready"}
