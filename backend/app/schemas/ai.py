from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TelemetrySnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    greenhouse_id: Optional[int]
    user_id: int
    temperature_avg: Optional[float]
    humidity_avg: Optional[float]
    samples_count: int
    window_started_at: datetime
    window_finished_at: datetime
    payload: Optional[Dict[str, Any]]
    created_at: datetime


class AIRecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    snapshot_id: int
    greenhouse_id: Optional[int]
    user_id: int
    model_name: str
    summary: str
    actions: str
    forecast: Optional[str]
    severity: Optional[str]
    created_at: datetime
    raw_prompt: Optional[Dict[str, Any]]
    raw_response: Optional[Dict[str, Any]]


class AIRecommendationList(BaseModel):
    items: List[AIRecommendationRead]
    total: int


class TelemetrySnapshotList(BaseModel):
    items: List[TelemetrySnapshotRead]
    total: int


class RunRecommendationResponse(BaseModel):
    recommendation: AIRecommendationRead
    snapshot: TelemetrySnapshotRead


class ManualTelemetryPayload(BaseModel):
    greenhouse_id: int = Field(..., ge=1)
    force_snapshot: bool = Field(default=True)
    force_recommendation: bool = Field(default=False)
