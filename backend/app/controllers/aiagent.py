from fastapi import APIRouter, Depends, HTTPException, Response, status
from ..services.aiagent import ollamachat
router = APIRouter(prefix="/ai", tags=["ai"])

@router.get("/tmp")
def tmpfunc():
    return ollamachat()