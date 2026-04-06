"""
Buyers API endpoints - Government entity profiles
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text

from app.database import get_db
from app.models.buyer import Buyer
from app.models.tender import Tender
from app.models.contractor import Contractor
from app.api._utils import paginate, tender_to_summary
from sqlalchemy.orm import joinedload

router = APIRouter()


def _parse_buyer_uuid(value: str):
    from uuid import UUID
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid buyer ID: {value}")


@router.get("/{buyer_id}")
async def get_buyer(
    buyer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Full profile for a government buyer."""
    uid = _parse_buyer_uuid(buyer_id)
    result = await db.execute(select(Buyer).where(Buyer.id == uid))
    buyer = result.scalar_one_or_none()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")

    total_tenders = await db.scalar(
        select(func.count(Tender.id)).where(Tender.buyer_id == uid)
    ) or 0
    total_value = await db.scalar(
        select(func.coalesce(func.sum(Tender.expected_value), 0)).where(Tender.buyer_id == uid)
    ) or 0
    avg_bids = await db.scalar(
        select(func.avg(Tender.num_bids)).where(
            Tender.buyer_id == uid, Tender.num_bids.isnot(None)
        )
    )
    high_risk_count = await db.scalar(
        select(func.count(Tender.id)).where(
            Tender.buyer_id == uid, Tender.risk_score >= 50
        )
    ) or 0
    single_bidder_count = await db.scalar(
        select(func.count(Tender.id)).where(
            Tender.buyer_id == uid, Tender.is_single_bidder.is_(True)
        )
    ) or 0

    return {
        "id": str(buyer.id),
        "prozorro_id": buyer.prozorro_id,
        "edrpou": buyer.edrpou,
        "name": buyer.name,
        "region": buyer.region,
        "address": buyer.address,
        "buyer_type": buyer.buyer_type,
        "total_tenders": total_tenders,
        "total_value": str(total_value),
        "avg_bids_per_tender": round(float(avg_bids), 2) if avg_bids else None,
        "high_risk_count": high_risk_count,
        "high_risk_rate": round(high_risk_count / max(total_tenders, 1) * 100),
        "single_bidder_count": single_bidder_count,
        "single_bidder_rate": round(single_bidder_count / max(total_tenders, 1) * 100),
    }


@router.get("/{buyer_id}/tenders")
async def get_buyer_tenders(
    buyer_id: str,
    status: Optional[str] = Query(None),
    risk_category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Tenders issued by this buyer, newest first."""
    uid = _parse_buyer_uuid(buyer_id)
    offset = (page - 1) * page_size

    from sqlalchemy import and_
    filters = [Tender.buyer_id == uid]
    if status:
        filters.append(Tender.status == status)
    if risk_category:
        filters.append(Tender.risk_category == risk_category)

    total = await db.scalar(
        select(func.count(Tender.id)).where(and_(*filters))
    ) or 0
    result = await db.execute(
        select(Tender)
        .options(joinedload(Tender.buyer), joinedload(Tender.winner))
        .where(and_(*filters))
        .order_by(Tender.date_modified.desc().nullslast())
        .offset(offset)
        .limit(page_size)
    )
    tenders = result.unique().scalars().all()

    return {
        "buyer_id": buyer_id,
        **paginate(total, page, page_size),
        "results": [tender_to_summary(t) for t in tenders],
    }


@router.get("/{buyer_id}/contractors")
async def get_buyer_contractors(
    buyer_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Top contractors this buyer has awarded contracts to."""
    uid = _parse_buyer_uuid(buyer_id)

    total_wins = await db.scalar(
        select(func.count(Tender.id)).where(
            Tender.buyer_id == uid, Tender.winner_id.isnot(None)
        )
    ) or 0

    result = await db.execute(
        select(
            Contractor.id,
            Contractor.name,
            Contractor.edrpou,
            Contractor.region,
            Contractor.risk_score,
            Contractor.risk_category,
            func.count(Tender.id).label("wins"),
            func.sum(Tender.award_value).label("total_value"),
        )
        .join(Tender, Tender.winner_id == Contractor.id)
        .where(Tender.buyer_id == uid)
        .group_by(
            Contractor.id, Contractor.name, Contractor.edrpou,
            Contractor.region, Contractor.risk_score, Contractor.risk_category,
        )
        .order_by(desc("wins"))
        .limit(limit)
    )

    rows = result.all()
    top_wins = rows[0].wins if rows else 0
    is_captured = top_wins >= 3 and (top_wins / max(total_wins, 1)) >= 0.5

    return {
        "buyer_id": buyer_id,
        "total_awarded": total_wins,
        "is_captured": is_captured,
        "capture_score": round(top_wins / max(total_wins, 1) * 100) if total_wins else 0,
        "contractors": [
            {
                "id": str(r.id),
                "name": r.name,
                "edrpou": r.edrpou,
                "region": r.region,
                "risk_score": float(r.risk_score) if r.risk_score else None,
                "risk_category": r.risk_category,
                "wins": r.wins,
                "total_value": str(r.total_value) if r.total_value else None,
                "share_pct": round(r.wins / max(total_wins, 1) * 100),
            }
            for r in rows
        ],
    }
