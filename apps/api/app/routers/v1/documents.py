"""Document endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.app.dependencies import get_db
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
) -> PaginatedResponse[DocumentResponse]:
    """List all documents."""
    # TODO: implement real DB query
    return PaginatedResponse[DocumentResponse].build(items=[], total=0, page=page, page_size=page_size)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db=Depends(get_db),
) -> DocumentResponse:
    """Get a single document by ID."""
    # TODO: implement real DB query
    raise HTTPException(status_code=404, detail="Document not found")
