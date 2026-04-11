"""Identity resolution tasks."""

import logging

from apps.worker.app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="identity_resolution.resolve_identities")
def resolve_identities(scope: dict) -> dict[str, str]:
    """Resolve identity candidates within a given scope.

    Evaluates candidate pairs and merges records that represent the
    same real-world entity, according to configured thresholds.
    """
    logger.info("Resolving identities with scope %s", scope)
    # TODO: implement real identity resolution
    return {"status": "ok", "message": f"Identity resolution complete for scope {scope}"}


@celery_app.task(name="identity_resolution.generate_identity_candidates")
def generate_identity_candidates(entity_type: str) -> dict[str, str]:
    """Generate identity-resolution candidates for an entity type.

    Runs blocking and similarity algorithms to produce candidate
    pairs for review or automated merging.
    """
    logger.info("Generating identity candidates for entity type %s", entity_type)
    # TODO: implement real candidate generation
    return {"status": "ok", "message": f"Candidates generated for {entity_type}"}
