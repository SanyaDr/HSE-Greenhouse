from __future__ import annotations

from typing import Iterable

from sqlalchemy import desc
from sqlmodel import Session, select

from ..models import AIRecommendation, TelemetrySnapshot


def save_snapshot(session: Session, snapshot: TelemetrySnapshot) -> TelemetrySnapshot:
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def save_recommendation(session: Session, recommendation: AIRecommendation) -> AIRecommendation:
    session.add(recommendation)
    session.commit()
    session.refresh(recommendation)
    return recommendation


def get_latest_snapshot_for_greenhouse(
    session: Session, greenhouse_id: int
) -> TelemetrySnapshot | None:
    statement = (
        select(TelemetrySnapshot)
        .where(TelemetrySnapshot.greenhouse_id == greenhouse_id)
        .order_by(desc(TelemetrySnapshot.created_at))
    )
    return session.exec(statement).first()


def get_latest_recommendation_for_greenhouse(
    session: Session, greenhouse_id: int
) -> AIRecommendation | None:
    statement = (
        select(AIRecommendation)
        .where(AIRecommendation.greenhouse_id == greenhouse_id)
        .order_by(desc(AIRecommendation.created_at))
    )
    return session.exec(statement).first()


def list_recommendations_for_user(
    session: Session,
    user_id: int,
    greenhouse_id: int | None = None,
    limit: int = 10,
) -> Iterable[AIRecommendation]:
    statement = (
        select(AIRecommendation)
        .where(AIRecommendation.user_id == user_id)
        .order_by(desc(AIRecommendation.created_at))
        .limit(limit)
    )
    if greenhouse_id is not None:
        statement = statement.where(AIRecommendation.greenhouse_id == greenhouse_id)
    return session.exec(statement).all()


def list_snapshots_for_user(
    session: Session,
    user_id: int,
    greenhouse_id: int | None = None,
    limit: int = 20,
) -> Iterable[TelemetrySnapshot]:
    statement = (
        select(TelemetrySnapshot)
        .where(TelemetrySnapshot.user_id == user_id)
        .order_by(desc(TelemetrySnapshot.created_at))
        .limit(limit)
    )
    if greenhouse_id is not None:
        statement = statement.where(TelemetrySnapshot.greenhouse_id == greenhouse_id)
    return session.exec(statement).all()
