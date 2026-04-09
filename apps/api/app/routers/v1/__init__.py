"""v1 API router — aggregates all resource routers."""

from fastapi import APIRouter

from apps.api.app.routers.v1.agenda_items import router as agenda_items_router
from apps.api.app.routers.v1.amendments import router as amendments_router
from apps.api.app.routers.v1.documents import router as documents_router
from apps.api.app.routers.v1.institutions import router as institutions_router
from apps.api.app.routers.v1.meetings import router as meetings_router
from apps.api.app.routers.v1.metrics import router as metrics_router
from apps.api.app.routers.v1.motions import router as motions_router
from apps.api.app.routers.v1.parties import router as parties_router
from apps.api.app.routers.v1.politicians import router as politicians_router
from apps.api.app.routers.v1.promises import router as promises_router
from apps.api.app.routers.v1.questions import router as questions_router
from apps.api.app.routers.v1.search import router as search_router
from apps.api.app.routers.v1.sources import router as sources_router
from apps.api.app.routers.v1.votes import router as votes_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(sources_router)
v1_router.include_router(institutions_router)
v1_router.include_router(meetings_router)
v1_router.include_router(agenda_items_router)
v1_router.include_router(documents_router)
v1_router.include_router(motions_router)
v1_router.include_router(amendments_router)
v1_router.include_router(questions_router)
v1_router.include_router(promises_router)
v1_router.include_router(votes_router)
v1_router.include_router(parties_router)
v1_router.include_router(politicians_router)
v1_router.include_router(metrics_router)
v1_router.include_router(search_router)
