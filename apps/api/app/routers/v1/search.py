"""Full-text search endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    """Body for full-text search."""

    query: str
    entity_types: list[str] | None = None
    page: int = 1
    page_size: int = 50


class SearchResultItem(BaseModel):
    """Single item in a search result set."""

    entity_type: str
    entity_id: str
    title: str
    snippet: str | None = None
    score: float | None = None


@router.post("", response_model=PaginatedResponse[SearchResultItem])
async def search(
    body: SearchRequest,
    db=Depends(get_db),
) -> PaginatedResponse[SearchResultItem]:
    """Search across entities (documents, motions, questions, etc.)."""
    # TODO: implement real full-text / vector search
    return PaginatedResponse[SearchResultItem].build(items=[], total=0, page=body.page, page_size=body.page_size)
