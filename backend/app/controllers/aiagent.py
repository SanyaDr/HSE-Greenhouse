from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from ..database import get_session
from ..schemas.ai import (
    AIRecommendationList,
    ManualTelemetryPayload,
    RunRecommendationResponse,
    TelemetrySnapshotList,
)
from ..security import get_current_user
from ..services.aiagent import (
    list_ai_recommendations,
    list_ai_snapshots,
    run_recommendation_for_greenhouse,
)
from ..services.greenhouses import get_greenhouse_for_user

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/recommendations", response_model=AIRecommendationList)
def read_recommendations(
    greenhouse_id: int | None = None,
    limit: int = 10,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AIRecommendationList:
    items = list_ai_recommendations(session, current_user.id, greenhouse_id, limit)
    return AIRecommendationList(items=items, total=len(items))


@router.get("/snapshots", response_model=TelemetrySnapshotList)
def read_snapshots(
    greenhouse_id: int | None = None,
    limit: int = 20,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TelemetrySnapshotList:
    items = list_ai_snapshots(session, current_user.id, greenhouse_id, limit)
    return TelemetrySnapshotList(items=items, total=len(items))


@router.post("/run", response_model=RunRecommendationResponse, status_code=status.HTTP_201_CREATED)
def run_manual_recommendation(
    payload: ManualTelemetryPayload,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RunRecommendationResponse:
    greenhouse = get_greenhouse_for_user(session, current_user.id, payload.greenhouse_id)
    if not greenhouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Теплица не найдена")

    snapshot, recommendation = run_recommendation_for_greenhouse(
        session,
        greenhouse,
        current_user.id,
        force_snapshot=payload.force_snapshot,
        force_recommendation=payload.force_recommendation,
    )
    if not recommendation:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="Новых рекомендаций нет")

    return RunRecommendationResponse(recommendation=recommendation, snapshot=snapshot)
