"""
Contractors API endpoints - Company profiles and details
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc, text
from sqlalchemy.orm import joinedload, selectinload

from app.database import get_db
from app.models.contractor import Contractor
from app.models.contractor_director import ContractorDirector
from app.models.tender import Tender
from app.models.bid import Bid
from app.models.co_bidding import CoBidding
from app.models.alert import Alert
from app.schemas import (
    ContractorDetail, ContractorSummary, ContractorEnrichment, DirectorSummary,
    NetworkGraph, NetworkNode, NetworkEdge,
    RiskCategory,
)
from app.api._utils import tender_to_summary

router = APIRouter()


def _parse_uuid(value: str, label: str = "ID") -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {label}: {value}")


# ── fixed-path routes first to avoid being caught by /{contractor_id} ──────────

@router.get("/high-risk", response_model=List[ContractorSummary])
async def get_high_risk_contractors(
    min_risk_score: int = Query(50, ge=0, le=100),
    min_wins: int = Query(1, ge=0),
    region: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get contractors with elevated risk scores."""
    filters = [
        Contractor.risk_score >= min_risk_score,
        Contractor.total_wins >= min_wins,
    ]
    if region:
        filters.append(Contractor.region == region)

    result = await db.execute(
        select(Contractor)
        .where(and_(*filters))
        .order_by(Contractor.risk_score.desc())
        .limit(limit)
    )
    return [ContractorSummary.model_validate(c) for c in result.scalars().all()]


@router.get("/by-edrpou/{edrpou}")
async def get_contractor_by_edrpou(
    edrpou: str,
    db: AsyncSession = Depends(get_db),
):
    """Look up contractor by EDRPOU (Ukrainian company registration number)."""
    result = await db.execute(
        select(Contractor).where(Contractor.edrpou == edrpou)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(status_code=404, detail=f"Contractor with EDRPOU {edrpou} not found")

    connections = await db.scalar(
        select(func.count()).where(
            or_(
                CoBidding.contractor_a_id == contractor.id,
                CoBidding.contractor_b_id == contractor.id,
            )
        )
    ) or 0

    return ContractorDetail(
        **ContractorSummary.model_validate(contractor).model_dump(),
        address=contractor.address,
        is_active=contractor.is_active or True,
        first_seen_at=contractor.first_seen_at,
        last_seen_at=contractor.last_seen_at,
        network_connections=connections,
    )


# ── parameterized routes ────────────────────────────────────────────────────────

@router.get("/{contractor_id}", response_model=ContractorDetail)
async def get_contractor(
    contractor_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full profile for a contractor."""
    uid = _parse_uuid(contractor_id)
    result = await db.execute(select(Contractor).where(Contractor.id == uid))
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    connections = await db.scalar(
        select(func.count()).where(
            or_(
                CoBidding.contractor_a_id == uid,
                CoBidding.contractor_b_id == uid,
            )
        )
    ) or 0

    return ContractorDetail(
        **ContractorSummary.model_validate(contractor).model_dump(),
        address=contractor.address,
        is_active=contractor.is_active or True,
        first_seen_at=contractor.first_seen_at,
        last_seen_at=contractor.last_seen_at,
        network_connections=connections,
    )


@router.get("/{contractor_id}/enrichment", response_model=ContractorEnrichment)
async def get_contractor_enrichment(
    contractor_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Sanctions, PEP, and EDR director enrichment for a contractor."""
    uid = _parse_uuid(contractor_id)
    result = await db.execute(select(Contractor).where(Contractor.id == uid))
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    directors_result = await db.execute(
        select(ContractorDirector)
        .where(ContractorDirector.contractor_id == uid)
        .order_by(ContractorDirector.role, ContractorDirector.full_name)
    )
    directors = [
        DirectorSummary.model_validate(d)
        for d in directors_result.scalars().all()
    ]

    return ContractorEnrichment(
        contractor_id=contractor_id,
        is_sanctioned=contractor.is_sanctioned or False,
        is_pep=contractor.is_pep or False,
        sanctions_hits=contractor.sanctions_hits or [],
        enriched_at=contractor.enriched_at,
        edr_status=contractor.edr_status,
        directors=directors,
        directors_fetched_at=contractor.directors_fetched_at,
    )


@router.get("/{contractor_id}/directors")
async def get_contractor_directors(
    contractor_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Company officers from the Ukrainian EDR registry."""
    uid = _parse_uuid(contractor_id)
    result = await db.execute(select(Contractor.id).where(Contractor.id == uid))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Contractor not found")

    directors_result = await db.execute(
        select(ContractorDirector)
        .where(ContractorDirector.contractor_id == uid)
        .order_by(ContractorDirector.role, ContractorDirector.full_name)
    )
    directors = [
        DirectorSummary.model_validate(d)
        for d in directors_result.scalars().all()
    ]
    return {"contractor_id": contractor_id, "directors": directors}


@router.get("/{contractor_id}/tenders")
async def get_contractor_tenders(
    contractor_id: str,
    status: Optional[str] = Query(None),
    won_only: bool = Query(False),
    risk_category: Optional[RiskCategory] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Tender history for a contractor (all bids or wins only)."""
    from app.api._utils import paginate
    uid = _parse_uuid(contractor_id)
    offset = (page - 1) * page_size

    if won_only:
        # Tenders this contractor won
        filters = [Tender.winner_id == uid]
        if status:
            filters.append(Tender.status == status)
        if risk_category:
            filters.append(Tender.risk_category == risk_category.value)

        total = await db.scalar(select(func.count(Tender.id)).where(and_(*filters))) or 0
        result = await db.execute(
            select(Tender)
            .options(joinedload(Tender.buyer), joinedload(Tender.winner))
            .where(and_(*filters))
            .order_by(Tender.date_modified.desc().nullslast())
            .offset(offset)
            .limit(page_size)
        )
        tenders = result.unique().scalars().all()
    else:
        # All tenders this contractor bid on (via bids table)
        filters = [Bid.contractor_id == uid]
        if risk_category:
            filters.append(Tender.risk_category == risk_category.value)
        if status:
            filters.append(Tender.status == status)

        total = await db.scalar(
            select(func.count(Bid.id))
            .join(Tender, Bid.tender_id == Tender.id)
            .where(and_(*filters))
        ) or 0
        result = await db.execute(
            select(Tender)
            .join(Bid, Bid.tender_id == Tender.id)
            .options(joinedload(Tender.buyer), joinedload(Tender.winner))
            .where(and_(*filters))
            .order_by(Tender.date_modified.desc().nullslast())
            .offset(offset)
            .limit(page_size)
        )
        tenders = result.unique().scalars().all()

    return {
        "contractor_id": contractor_id,
        **paginate(total, page, page_size),
        "results": [tender_to_summary(t) for t in tenders],
    }


@router.get("/{contractor_id}/network", response_model=NetworkGraph)
async def get_contractor_network(
    contractor_id: str,
    depth: int = Query(2, ge=1, le=3),
    max_nodes: int = Query(50, ge=10, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Co-bidding network for a contractor (alias for /api/network/{id})."""
    from app.api.network import build_network_graph
    return await build_network_graph(contractor_id, depth, max_nodes, db)


@router.get("/{contractor_id}/risk-factors")
async def get_contractor_risk_factors(
    contractor_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Detailed risk breakdown for a contractor."""
    uid = _parse_uuid(contractor_id)
    result = await db.execute(select(Contractor).where(Contractor.id == uid))
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(status_code=404, detail="Contractor not found")

    # Aggregate risk signals from their tenders
    tenders_result = await db.execute(
        select(Tender.risk_factors, Tender.risk_score)
        .where(Tender.winner_id == uid, Tender.risk_factors.isnot(None))
        .order_by(Tender.risk_score.desc())
        .limit(20)
    )
    tender_risks = tenders_result.all()

    # Summarize factor contributions
    factor_counts: dict = {}
    for row in tender_risks:
        if row.risk_factors:
            for key, val in row.risk_factors.items():
                if key not in factor_counts:
                    factor_counts[key] = {"total": 0, "count": 0}
                score = val.get("score", 0) if isinstance(val, dict) else 0
                factor_counts[key]["total"] += score
                factor_counts[key]["count"] += 1

    factors = {
        k: {
            "avg_score": round(v["total"] / v["count"], 2) if v["count"] else 0,
            "occurrences": v["count"],
        }
        for k, v in factor_counts.items()
    }

    return {
        "contractor_id": contractor_id,
        "risk_score": float(contractor.risk_score) if contractor.risk_score is not None else None,
        "risk_category": contractor.risk_category,
        "factors": factors,
    }


@router.get("/{contractor_id}/buyers")
async def get_contractor_buyers(
    contractor_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Government buyers this contractor has worked with, sorted by frequency."""
    from app.models.buyer import Buyer
    uid = _parse_uuid(contractor_id)

    result = await db.execute(
        select(
            Buyer.id,
            Buyer.name,
            Buyer.region,
            func.count(Tender.id).label("tender_count"),
            func.sum(Tender.award_value).label("total_value"),
        )
        .join(Tender, Tender.buyer_id == Buyer.id)
        .where(Tender.winner_id == uid)
        .group_by(Buyer.id, Buyer.name, Buyer.region)
        .order_by(desc("tender_count"))
        .limit(limit)
    )

    buyers = [
        {
            "id": str(row.id),
            "name": row.name,
            "region": row.region,
            "tender_count": row.tender_count,
            "total_value": str(row.total_value) if row.total_value else None,
        }
        for row in result.all()
    ]
    return {"contractor_id": contractor_id, "buyers": buyers, "total": len(buyers)}


@router.get("/{contractor_id}/capture-analysis")
async def get_capture_analysis(
    contractor_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Detect buyer-contractor capture: same buyer repeatedly awarding to same contractor."""
    from app.models.buyer import Buyer
    uid = _parse_uuid(contractor_id)

    total_wins = await db.scalar(
        select(func.count(Tender.id)).where(Tender.winner_id == uid)
    ) or 0

    result = await db.execute(
        select(
            Buyer.id,
            Buyer.name,
            Buyer.region,
            func.count(Tender.id).label("wins"),
            func.sum(Tender.award_value).label("total_value"),
        )
        .join(Tender, Tender.buyer_id == Buyer.id)
        .where(Tender.winner_id == uid)
        .group_by(Buyer.id, Buyer.name, Buyer.region)
        .order_by(desc("wins"))
        .limit(10)
    )
    rows = result.all()

    top_buyer_wins = rows[0].wins if rows else 0
    capture_score = round(top_buyer_wins / max(total_wins, 1) * 100) if total_wins > 0 else 0
    is_flagged = capture_score >= 50 and top_buyer_wins >= 3

    return {
        "contractor_id": contractor_id,
        "total_wins": total_wins,
        "capture_score": capture_score,
        "is_flagged": is_flagged,
        "top_buyers": [
            {
                "id": str(r.id),
                "name": r.name,
                "region": r.region,
                "wins": r.wins,
                "total_value": str(r.total_value) if r.total_value else None,
                "share_pct": round(r.wins / max(total_wins, 1) * 100),
            }
            for r in rows
        ],
    }


@router.get("/{contractor_id}/bid-rotation")
async def get_bid_rotation(
    contractor_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Detect bid rotation patterns: contractor alternating wins with regular co-bidders."""
    uid = _parse_uuid(contractor_id)

    result = await db.execute(
        text("""
        WITH shared AS (
            SELECT
                b2.contractor_id AS partner_id,
                t.winner_id,
                t.id            AS tender_id
            FROM bids b1
            JOIN bids b2 ON b1.tender_id = b2.tender_id
                         AND b2.contractor_id != b1.contractor_id
            JOIN tenders t ON t.id = b1.tender_id
            WHERE b1.contractor_id = :uid
              AND t.winner_id IN (b1.contractor_id, b2.contractor_id)
              AND t.winner_id IS NOT NULL
        ),
        stats AS (
            SELECT
                partner_id,
                COUNT(DISTINCT tender_id)                                              AS shared_wins,
                SUM(CASE WHEN winner_id = :uid         THEN 1 ELSE 0 END)             AS our_wins,
                SUM(CASE WHEN winner_id = partner_id   THEN 1 ELSE 0 END)             AS partner_wins
            FROM shared
            GROUP BY partner_id
            HAVING COUNT(DISTINCT tender_id) >= 3
               AND SUM(CASE WHEN winner_id = :uid       THEN 1 ELSE 0 END) > 0
               AND SUM(CASE WHEN winner_id = partner_id THEN 1 ELSE 0 END) > 0
        )
        SELECT
            s.partner_id,
            c.name           AS partner_name,
            c.edrpou         AS partner_edrpou,
            c.risk_score,
            c.risk_category,
            s.shared_wins,
            s.our_wins,
            s.partner_wins
        FROM stats s
        JOIN contractors c ON c.id = s.partner_id
        ORDER BY s.shared_wins DESC
        LIMIT 10
        """),
        {"uid": str(uid)},
    )
    rows = result.mappings().all()

    suspects = []
    for r in rows:
        our = r["our_wins"]
        theirs = r["partner_wins"]
        balance = round(min(our, theirs) / max(our, theirs), 2) if max(our, theirs) > 0 else 0
        suspects.append({
            "partner_id": str(r["partner_id"]),
            "partner_name": r["partner_name"],
            "partner_edrpou": r["partner_edrpou"],
            "risk_score": float(r["risk_score"]) if r["risk_score"] else None,
            "risk_category": r["risk_category"],
            "shared_wins": r["shared_wins"],
            "our_wins": our,
            "partner_wins": theirs,
            "balance_score": balance,
        })

    flagged = [s for s in suspects if s["balance_score"] >= 0.5]
    return {
        "contractor_id": contractor_id,
        "rotation_suspects": suspects,
        "flagged_count": len(flagged),
        "is_flagged": len(flagged) > 0,
    }


@router.get("/{contractor_id}/timeline")
async def get_contractor_timeline(
    contractor_id: str,
    period: str = Query("1y", regex="^(3m|6m|1y|all)$"),
    db: AsyncSession = Depends(get_db),
):
    """Activity timeline (bids and wins over time)."""
    uid = _parse_uuid(contractor_id)

    period_days = {"3m": 90, "6m": 180, "1y": 365, "all": 36500}
    since = datetime.now(timezone.utc) - timedelta(days=period_days[period])

    result = await db.execute(
        select(
            Bid.bid_date,
            Bid.bid_value,
            Bid.is_winner,
            Tender.title,
            Tender.prozorro_id,
            Tender.risk_score,
        )
        .join(Tender, Bid.tender_id == Tender.id)
        .where(Bid.contractor_id == uid, Bid.bid_date >= since)
        .order_by(Bid.bid_date.desc())
    )

    events = [
        {
            "date": row.bid_date.isoformat() if row.bid_date else None,
            "type": "win" if row.is_winner else "bid",
            "value": str(row.bid_value) if row.bid_value else None,
            "tender_title": row.title,
            "tender_id": row.prozorro_id,
            "risk_score": float(row.risk_score) if row.risk_score is not None else None,
        }
        for row in result.all()
    ]

    return {
        "contractor_id": contractor_id,
        "period": period,
        "events": events,
        "total": len(events),
    }

