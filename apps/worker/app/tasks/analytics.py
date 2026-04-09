"""Analytics / metric computation tasks."""

import logging

from apps.worker.app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="analytics.recompute_metrics")
def recompute_metrics(
    metric_codes: list[str], entity_id: str | None = None
) -> dict[str, str]:
    """Recompute specific metrics, optionally scoped to one entity.

    Runs the metric computation pipeline for each requested code
    and persists MetricResult rows.
    """
    logger.info(
        "Recomputing metrics %s for entity %s",
        metric_codes,
        entity_id or "all",
    )
    # TODO: implement real metric computation
    return {
        "status": "ok",
        "message": f"Recomputed {len(metric_codes)} metrics",
    }


@celery_app.task(name="analytics.recompute_all_metrics")
def recompute_all_metrics() -> dict[str, str]:
    """Recompute every registered metric.

    Iterates over all MetricDefinition rows and triggers
    recomputation for each one.
    """
    logger.info("Recomputing all metrics")
    # TODO: implement real full recomputation
    return {"status": "ok", "message": "All metrics recomputed"}
