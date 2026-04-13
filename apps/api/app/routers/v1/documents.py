"""Document endpoints."""

from uuid import UUID

from curia_domain.db.models import DocumentRow
from curia_domain.enums import DocumentType
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.dependencies import get_db
from apps.api.app.routers.v1._utils import fetch_one_or_404, fetch_paginated
from apps.api.app.schemas.common import PaginatedResponse
from apps.api.app.schemas.responses import DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=PaginatedResponse[DocumentResponse])
async def list_documents(
    meeting_id: UUID | None = Query(None, description="Filter by meeting"),
    agenda_item_id: UUID | None = Query(None, description="Filter by agenda item"),
    document_type: DocumentType | None = Query(None, description="Filter by document type"),
    text_extracted: bool | None = Query(None, description="Filter by extraction status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[DocumentResponse]:
    """List all documents."""
    stmt = select(DocumentRow).order_by(DocumentRow.created_at, DocumentRow.id)

    if meeting_id is not None:
        stmt = stmt.where(DocumentRow.meeting_id == meeting_id)
    if agenda_item_id is not None:
        stmt = stmt.where(DocumentRow.agenda_item_id == agenda_item_id)
    if document_type is not None:
        stmt = stmt.where(DocumentRow.document_type == document_type)
    if text_extracted is not None:
        stmt = stmt.where(DocumentRow.text_extracted == text_extracted)

    return await fetch_paginated(db, stmt, DocumentResponse, limit=limit, offset=offset)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Get a single document by ID."""
    return await fetch_one_or_404(
        db,
        select(DocumentRow).where(DocumentRow.id == document_id),
        DocumentResponse,
        detail="Document not found",
    )
