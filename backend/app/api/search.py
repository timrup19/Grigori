"""
Search API endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.database import get_db
from app.schemas import (
    ContractorSearchResponse, ContractorSummary,
    TenderSearchResponse, TenderSummary,
    UnifiedSearchResponse, UnifiedSearchResult,
    RiskCategory, PaginationParams
)

router = APIRouter()


@router.get("/contractors", response_model=ContractorSearchResponse)
async def search_contractors(
    q: str = Query(..., min_length=2, description="Search query"),
    region: Optional[str] = Query(None, description="Filter by region"),
    risk_category: Optional[RiskCategory] = Query(None, description="Filter by risk category"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Search contractors by name or EDRPOU.
    
    - **q**: Search query (name or EDRPOU code)
    - **region**: Filter by region
    - **risk_category**: Filter by risk level
    """
    # TODO: Implement actual database query
    # This is a placeholder structure
    
    return ContractorSearchResponse(
        total=0,
        page=page,
        page_size=page_size,
        total_pages=0,
        has_next=False,
        has_prev=False,
        results=[]
    )


@router.get("/tenders", response_model=TenderSearchResponse)
async def search_tenders(
    q: str = Query(..., min_length=2, description="Search query"),
    region: Optional[str] = Query(None, description="Filter by region"),
    risk_category: Optional[RiskCategory] = Query(None, description="Filter by risk category"),
    cpv_code: Optional[str] = Query(None, description="Filter by CPV code"),
    min_value: Optional[float] = Query(None, description="Minimum contract value"),
    max_value: Optional[float] = Query(None, description="Maximum contract value"),
    single_bidder_only: bool = Query(False, description="Only single-bidder tenders"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Search tenders by title, Prozorro ID, or buyer name.
    
    - **q**: Search query
    - **region**: Filter by region
    - **risk_category**: Filter by risk level
    - **cpv_code**: Filter by procurement category
    - **min_value** / **max_value**: Filter by contract value
    - **single_bidder_only**: Only show non-competitive tenders
    """
    # TODO: Implement actual database query
    
    return TenderSearchResponse(
        total=0,
        page=page,
        page_size=page_size,
        total_pages=0,
        has_next=False,
        has_prev=False,
        results=[]
    )


@router.get("/buyers")
async def search_buyers(
    q: str = Query(..., min_length=2, description="Search query"),
    region: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Search government buyers/procuring entities.
    """
    # TODO: Implement actual database query
    
    return {
        "total": 0,
        "page": page,
        "page_size": page_size,
        "total_pages": 0,
        "has_next": False,
        "has_prev": False,
        "results": []
    }


@router.get("/unified", response_model=UnifiedSearchResponse)
async def unified_search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Unified search across contractors, tenders, and buyers.
    Returns mixed results for autocomplete/quick search.
    """
    # TODO: Implement unified search across all entities
    
    return UnifiedSearchResponse(
        query=q,
        total=0,
        results=[]
    )


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2),
    type: Optional[str] = Query(None, description="Entity type: contractor, tender, buyer"),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """
    Quick autocomplete suggestions.
    Returns minimal data for fast typeahead.
    """
    # TODO: Implement autocomplete
    
    return {
        "query": q,
        "suggestions": []
    }
