"""
Search API endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.contractor import Contractor
from app.models.tender import Tender
from app.models.buyer import Buyer
from app.schemas import (
    ContractorSearchResponse, ContractorSummary,
    TenderSearchResponse,
    UnifiedSearchResponse, UnifiedSearchResult,
    RiskCategory,
)
from app.api._utils import paginate, tender_to_summary

router = APIRouter()


@router.get("/contractors", response_model=ContractorSearchResponse)
async def search_contractors(
    q: str = Query(..., min_length=2, description="Search query (name or EDRPOU)"),
    region: Optional[str] = Query(None),
    risk_category: Optional[RiskCategory] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    q_lower = q.lower().strip()

    filters = [
        or_(
            Contractor.name_normalized.ilike(f"%{q_lower}%"),
            Contractor.edrpou == q.strip(),
        )
    ]
    if region:
        filters.append(Contractor.region == region)
    if risk_category:
        filters.append(Contractor.risk_category == risk_category.value)

    where = and_(*filters)

    total = await db.scalar(select(func.count(Contractor.id)).where(where)) or 0

    result = await db.execute(
        select(Contractor)
        .where(where)
        .order_by(Contractor.risk_score.desc().nullslast())
        .offset(offset)
        .limit(page_size)
    )
    contractors = result.scalars().all()

    return ContractorSearchResponse(
        results=[ContractorSummary.model_validate(c) for c in contractors],
        **paginate(total, page, page_size),
    )


@router.get("/tenders", response_model=TenderSearchResponse)
async def search_tenders(
    q: str = Query(..., min_length=2, description="Search query"),
    region: Optional[str] = Query(None),
    risk_category: Optional[RiskCategory] = Query(None),
    cpv_code: Optional[str] = Query(None),
    min_value: Optional[float] = Query(None),
    max_value: Optional[float] = Query(None),
    single_bidder_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size

    filters = [Tender.title.ilike(f"%{q}%")]
    if region:
        filters.append(Tender.region == region)
    if risk_category:
        filters.append(Tender.risk_category == risk_category.value)
    if cpv_code:
        filters.append(Tender.cpv_code.startswith(cpv_code))
    if min_value is not None:
        filters.append(Tender.expected_value >= min_value)
    if max_value is not None:
        filters.append(Tender.expected_value <= max_value)
    if single_bidder_only:
        filters.append(Tender.is_single_bidder.is_(True))

    where = and_(*filters)

    total = await db.scalar(select(func.count(Tender.id)).where(where)) or 0

    result = await db.execute(
        select(Tender)
        .options(joinedload(Tender.buyer), joinedload(Tender.winner))
        .where(where)
        .order_by(Tender.risk_score.desc().nullslast())
        .offset(offset)
        .limit(page_size)
    )
    tenders = result.unique().scalars().all()

    return TenderSearchResponse(
        results=[tender_to_summary(t) for t in tenders],
        **paginate(total, page, page_size),
    )


@router.get("/buyers")
async def search_buyers(
    q: str = Query(..., min_length=2),
    region: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    q_lower = q.lower().strip()

    filters = [Buyer.name_normalized.ilike(f"%{q_lower}%")]
    if region:
        filters.append(Buyer.region == region)

    where = and_(*filters)
    total = await db.scalar(select(func.count(Buyer.id)).where(where)) or 0

    result = await db.execute(
        select(Buyer)
        .where(where)
        .order_by(Buyer.total_tenders.desc().nullslast())
        .offset(offset)
        .limit(page_size)
    )
    buyers = result.scalars().all()

    return {
        **paginate(total, page, page_size),
        "results": [
            {
                "id": str(b.id),
                "name": b.name,
                "region": b.region,
                "total_tenders": b.total_tenders,
                "total_value": str(b.total_value) if b.total_value else None,
                "buyer_type": b.buyer_type,
            }
            for b in buyers
        ],
    }


@router.get("/unified", response_model=UnifiedSearchResponse)
async def unified_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    q_lower = q.lower().strip()
    per_type = max(limit // 3, 3)
    results = []

    c_result = await db.execute(
        select(Contractor)
        .where(
            or_(
                Contractor.name_normalized.ilike(f"%{q_lower}%"),
                Contractor.edrpou == q.strip(),
            )
        )
        .order_by(Contractor.risk_score.desc().nullslast())
        .limit(per_type)
    )
    for c in c_result.scalars().all():
        results.append(UnifiedSearchResult(
            type="contractor",
            id=str(c.id),
            name=c.name,
            subtitle=f"ЄДРПОУ: {c.edrpou}" + (f" • {c.region}" if c.region else ""),
            risk_score=float(c.risk_score) if c.risk_score is not None else None,
            risk_category=c.risk_category,
        ))

    t_result = await db.execute(
        select(Tender)
        .where(Tender.title.ilike(f"%{q}%"))
        .order_by(Tender.risk_score.desc().nullslast())
        .limit(per_type)
    )
    for t in t_result.scalars().all():
        results.append(UnifiedSearchResult(
            type="tender",
            id=str(t.id),
            name=t.title or t.prozorro_id,
            subtitle=t.prozorro_id,
            risk_score=float(t.risk_score) if t.risk_score is not None else None,
            risk_category=t.risk_category,
        ))

    b_result = await db.execute(
        select(Buyer)
        .where(Buyer.name_normalized.ilike(f"%{q_lower}%"))
        .limit(per_type)
    )
    for b in b_result.scalars().all():
        results.append(UnifiedSearchResult(
            type="buyer",
            id=str(b.id),
            name=b.name,
            subtitle=b.region,
        ))

    return UnifiedSearchResponse(query=q, total=len(results), results=results[:limit])


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2),
    type: Optional[str] = Query(None, description="contractor | tender | buyer"),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    q_lower = q.lower().strip()
    suggestions = []

    if not type or type == "contractor":
        result = await db.execute(
            select(Contractor.id, Contractor.name, Contractor.edrpou)
            .where(Contractor.name_normalized.ilike(f"%{q_lower}%"))
            .limit(limit)
        )
        for row in result.all():
            suggestions.append({
                "type": "contractor",
                "id": str(row.id),
                "label": row.name,
                "meta": f"ЄДРПОУ {row.edrpou}",
            })

    if not type or type == "tender":
        result = await db.execute(
            select(Tender.id, Tender.title, Tender.prozorro_id)
            .where(Tender.title.ilike(f"%{q}%"))
            .limit(limit)
        )
        for row in result.all():
            suggestions.append({
                "type": "tender",
                "id": str(row.id),
                "label": row.title or row.prozorro_id,
                "meta": row.prozorro_id,
            })

    return {"query": q, "suggestions": suggestions[:limit]}
