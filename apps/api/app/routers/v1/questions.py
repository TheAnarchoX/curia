"""Written-question endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import WrittenQuestionResponse

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("", response_model=PaginatedResponse[WrittenQuestionResponse])
async def list_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[WrittenQuestionResponse]:
    """List all written questions."""
    # TODO: implement real DB query
    return PaginatedResponse[WrittenQuestionResponse].build(
        items=[], total=0, page=page, page_size=page_size
    )


@router.get("/{question_id}", response_model=WrittenQuestionResponse)
async def get_question(
    question_id: UUID,
    db=Depends(get_db),
) -> WrittenQuestionResponse:
    """Get a single written question by ID."""
    # TODO: implement real DB query
    raise HTTPException(status_code=404, detail="Written question not found")
