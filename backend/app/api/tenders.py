"""
Tenders API endpoints - Individual tender detail
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.tender import Tender
from app.models.bid import Bid

router = APIRouter()


@router.get("/{tender_id}")
async def get_tender(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Full detail for a single tender including bids, buyer, and winner."""
    try:
        uid = UUID(tender_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tender ID: {tender_id}")

    result = await db.execute(
        select(Tender)
        .options(
            joinedload(Tender.buyer),
            joinedload(Tender.winner),
            joinedload(Tender.bids).joinedload(Bid.contractor),
        )
        .where(Tender.id == uid)
    )
    tender = result.unique().scalar_one_or_none()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    bids = sorted(
        [
            {
                "id": str(b.id),
                "contractor_id": str(b.contractor_id),
                "contractor_name": b.contractor.name if b.contractor else None,
                "contractor_edrpou": b.contractor.edrpou if b.contractor else None,
                "bid_value": str(b.bid_value) if b.bid_value else None,
                "is_winner": b.is_winner,
            }
            for b in tender.bids
        ],
        key=lambda b: (not b["is_winner"], float(b["bid_value"] or 0)),
    )

    risk_factors = tender.risk_factors or {}

    return {
        "id": str(tender.id),
        "prozorro_id": tender.prozorro_id,
        "title": tender.title,
        "description": tender.description,
        "status": tender.status,
        "procurement_method": tender.procurement_method,
        "procurement_method_type": tender.procurement_method_type,
        "expected_value": str(tender.expected_value) if tender.expected_value else None,
        "award_value": str(tender.award_value) if tender.award_value else None,
        "currency": tender.currency or "UAH",
        "cpv_code": tender.cpv_code,
        "cpv_description": tender.cpv_description,
        "region": tender.region,
        "num_bids": tender.num_bids or 0,
        "is_single_bidder": tender.is_single_bidder or False,
        "is_price_anomaly": tender.is_price_anomaly or False,
        "is_bid_pattern_anomaly": tender.is_bid_pattern_anomaly or False,
        "tender_start_date": tender.tender_start_date.isoformat() if tender.tender_start_date else None,
        "tender_end_date": tender.tender_end_date.isoformat() if tender.tender_end_date else None,
        "award_date": tender.award_date.isoformat() if tender.award_date else None,
        "date_modified": tender.date_modified.isoformat() if tender.date_modified else None,
        "risk_score": float(tender.risk_score) if tender.risk_score is not None else None,
        "risk_category": tender.risk_category,
        "risk_reasons": risk_factors.get("reasons", []),
        "risk_factors": risk_factors,
        "buyer": {
            "id": str(tender.buyer.id),
            "name": tender.buyer.name,
            "region": tender.buyer.region,
        } if tender.buyer else None,
        "winner": {
            "id": str(tender.winner.id),
            "name": tender.winner.name,
            "edrpou": tender.winner.edrpou,
            "risk_score": float(tender.winner.risk_score) if tender.winner.risk_score is not None else None,
            "risk_category": tender.winner.risk_category,
        } if tender.winner else None,
        "bids": bids,
    }
