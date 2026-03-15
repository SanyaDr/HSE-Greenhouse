from __future__ import annotations

import asyncio
import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import Iterable

import httpx
from ollama import chat
from sqlmodel import Session, select

from ..config import Settings
from ..database import engine
from ..models import AIRecommendation, Greenhouse, TelemetrySnapshot
from ..repositories.ai import (
    get_latest_recommendation_for_greenhouse,
    get_latest_snapshot_for_greenhouse,
    list_recommendations_for_user,
    list_snapshots_for_user,
    save_recommendation,
    save_snapshot,
)
from ..repositories.devices import list_for_user_and_greenhouse
from ..services.telemetry import get_device_telemetry

logger = logging.getLogger(__name__)
settings = Settings()


def _collect_numeric(samples: Iterable, limit: int | None = None) -> list[float]:
    values: list[float] = []
    for sample in samples:
        value = sample.value if hasattr(sample, "value") else sample.get("value")
        if value is None:
            continue
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue
        if limit and len(values) >= limit:
            break
    return values


def _aggregate_telemetry(session: Session, greenhouse: Greenhouse, user_id: int) -> TelemetrySnapshot | None:
    devices = list_for_user_and_greenhouse(session, user_id, greenhouse.id)
    if not devices:
        return None

    all_temperatures: list[float] = []
    all_humidities: list[float] = []
    payload: dict[str, list[float]] = {}
    anchor_device_id = next((device.id for device in devices if device.id is not None), devices[0].id)

    for device in devices:
        try:
            telemetry = get_device_telemetry(session, user_id, device.id)
        except Exception as exc:
            logger.debug(
                "Телеметрия недоступна для устройства %s: %s", device.serial_number, exc
            )
            continue

        for key, samples in telemetry.telemetry.items():
            values = _collect_numeric(samples)
            payload.setdefault(key, []).extend(values)
            key_lower = key.lower()
            if "temp" in key_lower:
                all_temperatures.extend(values)
            if "humid" in key_lower:
                all_humidities.extend(values)

    if not all_temperatures and not all_humidities:
        return None

    window_finished = datetime.now(timezone.utc)
    window_started = window_finished - timedelta(minutes=settings.ai_snapshot_window_minutes)

    snapshot = TelemetrySnapshot(
        device_id=anchor_device_id,
        greenhouse_id=greenhouse.id,
        user_id=user_id,
        temperature_avg=statistics.fmean(all_temperatures) if all_temperatures else None,
        humidity_avg=statistics.fmean(all_humidities) if all_humidities else None,
        samples_count=len(all_temperatures) + len(all_humidities),
        window_started_at=window_started,
        window_finished_at=window_finished,
        payload=payload or None,
    )
    return save_snapshot(session, snapshot)


def _should_skip_snapshot(last_snapshot: TelemetrySnapshot | None) -> bool:
    if not last_snapshot:
        return False
    delta = datetime.utcnow() - last_snapshot.created_at
    return delta.total_seconds() < settings.ai_snapshot_interval_seconds


def _should_skip_recommendation(last_recommendation: AIRecommendation | None) -> bool:
    if not last_recommendation:
        return False
    delta = datetime.utcnow() - last_recommendation.created_at
    return delta.total_seconds() < settings.ai_recommendation_cooldown_minutes * 60


def _format_prompt(snapshot: TelemetrySnapshot, greenhouse: Greenhouse) -> list[dict[str, str]]:
    summary_parts = []
    if snapshot.temperature_avg is not None:
        summary_parts.append(f"средняя температура {snapshot.temperature_avg:.1f} °C")
    if snapshot.humidity_avg is not None:
        summary_parts.append(f"средняя влажность {snapshot.humidity_avg:.1f} %")
    summary = ", ".join(summary_parts) if summary_parts else "данных мало"

    user_content = (
        f"Теплица: {greenhouse.name}. Пользователь ожидает рекомендации по температуре и влажности. "
        f"Период наблюдения: {snapshot.window_started_at} — {snapshot.window_finished_at}. "
        f"Сводка: {summary}. Подробные выборки: {snapshot.payload}."
    )

    messages = [
        {"role": "system", "content": settings.ai_agent_system_prompt},
        {"role": "user", "content": user_content},
    ]
    return messages


def _call_ollama(messages: list[dict[str, str]]) -> str:
    try:
        response = chat(
            model=settings.ai_agent_model,
            messages=messages,
            stream=False,
            options={
                "temperature": settings.ai_agent_temperature,
                "num_predict": settings.ai_agent_max_tokens,
            },
        )
        return response.get("message", {}).get("content", "")
    except httpx.HTTPError as exc:
        logger.error("Ollama HTTP error: %s", exc)
        raise
    except Exception as exc:
        logger.error("Ollama invocation failed: %s", exc)
        raise


def _parse_ollama_response(text: str) -> tuple[str, str, str | None, str | None]:
    sections = {
        "summary": "",
        "actions": "",
        "forecast": None,
        "severity": None,
    }
    current_key = None
    for line in text.splitlines():
        line_strip = line.strip().lower()
        if line_strip.startswith("резюме"):
            current_key = "summary"
            continue
        if line_strip.startswith("действ"):
            current_key = "actions"
            continue
        if line_strip.startswith("прогноз"):
            current_key = "forecast"
            continue
        if line_strip.startswith("риск") or "опас" in line_strip:
            current_key = "severity"
            continue
        if current_key:
            existing = sections[current_key] or ""
            sections[current_key] = f"{existing}\n{line.strip()}".strip()
    return (
        sections["summary"],
        sections["actions"],
        sections["forecast"],
        sections["severity"],
    )


def run_recommendation_for_greenhouse(
    session: Session,
    greenhouse: Greenhouse,
    user_id: int,
    *,
    force_snapshot: bool = False,
    force_recommendation: bool = False,
) -> tuple[TelemetrySnapshot, AIRecommendation]:
    last_snapshot = get_latest_snapshot_for_greenhouse(session, greenhouse.id)
    if not force_snapshot and _should_skip_snapshot(last_snapshot):
        snapshot = last_snapshot
    else:
        snapshot = _aggregate_telemetry(session, greenhouse, user_id)
    if not snapshot:
        raise RuntimeError("Недостаточно телеметрии для рекомендации")

    last_recommendation = get_latest_recommendation_for_greenhouse(session, greenhouse.id)
    if not force_recommendation and _should_skip_recommendation(last_recommendation):
        if last_recommendation:
            return snapshot, last_recommendation
        raise RuntimeError("Рекомендации уже актуальны")

    messages = _format_prompt(snapshot, greenhouse)
    raw_response = _call_ollama(messages)
    summary, actions, forecast, severity = _parse_ollama_response(raw_response)

    recommendation = AIRecommendation(
        snapshot_id=snapshot.id,
        greenhouse_id=greenhouse.id,
        user_id=user_id,
        model_name=settings.ai_agent_model,
        summary=summary or "Нет явного резюме",
        actions=actions or "Нет конкретных действий",
        forecast=forecast,
        severity=severity,
        raw_prompt={"messages": messages},
        raw_response={"text": raw_response},
    )
    recommendation = save_recommendation(session, recommendation)
    return snapshot, recommendation


def run_ai_agent_cycle() -> None:
    with Session(engine) as session:
        greenhouses = session.exec(select(Greenhouse)).all()
        for greenhouse in greenhouses:
            try:
                run_recommendation_for_greenhouse(session, greenhouse, greenhouse.user_id)
            except Exception:
                logger.exception("AI recommendation failed for greenhouse %s", greenhouse.id)


async def start_ai_agent_loop(interval_seconds: int | None = None) -> None:
    interval = interval_seconds or settings.ai_agent_loop_interval_seconds
    while True:
        if not settings.ai_agent_enabled:
            await asyncio.sleep(interval)
            continue
        try:
            await asyncio.to_thread(run_ai_agent_cycle)
        except Exception:
            logger.exception("AI agent loop failure")
        await asyncio.sleep(interval)


def list_ai_recommendations(
    session: Session, user_id: int, greenhouse_id: int | None = None, limit: int = 10
):
    items = list_recommendations_for_user(session, user_id, greenhouse_id, limit)
    return items


def list_ai_snapshots(
    session: Session, user_id: int, greenhouse_id: int | None = None, limit: int = 20
):
    items = list_snapshots_for_user(session, user_id, greenhouse_id, limit)
    return items
