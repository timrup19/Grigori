"""
Statistics API endpoints - Platform-wide metrics
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, desc, text

from app.database import get_db
from app.models.contractor import Contractor
from app.models.tender import Tender
from app.models.buyer import Buyer
from app.models.alert import Alert
from app.models.sync_log import SyncLog
from app.schemas import OverviewStats, RiskDistribution

router = APIRouter()


@router.get("/overview", response_model=OverviewStats)
async def get_overview_stats(
    db: AsyncSession = Depends(get_db),
):
    """Platform-wide overview statistics for the main dashboard."""
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    total_tenders = await db.scalar(select(func.count(Tender.id))) or 0
    total_contractors = await db.scalar(select(func.count(Contractor.id))) or 0
    total_value = await db.scalar(
        select(func.coalesce(func.sum(Tender.expected_value), 0))
    ) or 0
    total_alerts = await db.scalar(
        select(func.count(Alert.id)).where(Alert.is_active.is_(True))
    ) or 0

    # Risk breakdown
    risk_counts = await db.execute(
        select(Tender.risk_category, func.count(Tender.id).label("cnt"))
        .where(Tender.risk_category.isnot(None))
        .group_by(Tender.risk_category)
    )
    risk_map = {row.risk_category: row.cnt for row in risk_counts.all()}

    # Single-bidder rate
    single_bidder_count = await db.scalar(
        select(func.count(Tender.id)).where(Tender.is_single_bidder.is_(True))
    ) or 0
    single_bidder_rate = single_bidder_count / total_tenders if total_tenders else 0.0

    # Average bids per tender
    avg_bids = await db.scalar(
        select(func.avg(Tender.num_bids)).where(Tender.num_bids > 0)
    ) or 0.0

    # Last 24h counts
    tenders_24h = await db.scalar(
        select(func.count(Tender.id)).where(Tender.created_at >= since_24h)
    ) or 0
    alerts_24h = await db.scalar(
        select(func.count(Alert.id)).where(Alert.detected_at >= since_24h)
    ) or 0

    # Last sync
    last_sync_result = await db.execute(
        select(SyncLog.completed_at)
        .where(SyncLog.status == "completed")
        .order_by(SyncLog.completed_at.desc())
        .limit(1)
    )
    last_sync_row = last_sync_result.scalar_one_or_none()

    return OverviewStats(
        total_tenders=total_tenders,
        total_contractors=total_contractors,
        total_value=total_value,
        total_alerts=total_alerts,
        low_risk_count=risk_map.get("low", 0),
        medium_risk_count=risk_map.get("medium", 0),
        high_risk_count=risk_map.get("high", 0),
        critical_risk_count=risk_map.get("critical", 0),
        single_bidder_rate=round(single_bidder_rate, 4),
        avg_bids_per_tender=round(float(avg_bids), 2),
        last_sync=last_sync_row,
        tenders_last_24h=tenders_24h,
        alerts_last_24h=alerts_24h,
    )


@router.get("/risk-distribution", response_model=RiskDistribution)
async def get_risk_distribution(
    db: AsyncSession = Depends(get_db),
):
    """Risk score distribution histogram across all scored tenders."""
    # Build buckets using CASE WHEN
    bucket_expr = case(
        (Tender.risk_score.between(0, 10), "0-10"),
        (Tender.risk_score.between(11, 20), "11-20"),
        (Tender.risk_score.between(21, 30), "21-30"),
        (Tender.risk_score.between(31, 40), "31-40"),
        (Tender.risk_score.between(41, 50), "41-50"),
        (Tender.risk_score.between(51, 60), "51-60"),
        (Tender.risk_score.between(61, 70), "61-70"),
        (Tender.risk_score.between(71, 80), "71-80"),
        (Tender.risk_score.between(81, 90), "81-90"),
        (Tender.risk_score.between(91, 100), "91-100"),
        else_="unknown",
    )

    result = await db.execute(
        select(bucket_expr.label("range"), func.count(Tender.id).label("count"))
        .where(Tender.risk_score.isnot(None))
        .group_by("range")
    )
    counts = {row.range: row.count for row in result.all()}

    ordered_ranges = [
        "0-10", "11-20", "21-30", "31-40", "41-50",
        "51-60", "61-70", "71-80", "81-90", "91-100",
    ]
    buckets = [{"range": r, "count": counts.get(r, 0)} for r in ordered_ranges]

    stats = await db.execute(
        select(
            func.avg(Tender.risk_score).label("mean"),
            func.percentile_cont(0.5).within_group(Tender.risk_score).label("median"),
            func.stddev(Tender.risk_score).label("std"),
        ).where(Tender.risk_score.isnot(None))
    )
    row = stats.one()

    return RiskDistribution(
        buckets=buckets,
        mean=round(float(row.mean), 2) if row.mean else 0.0,
        median=round(float(row.median), 2) if row.median else 0.0,
        std=round(float(row.std), 2) if row.std else 0.0,
    )


@router.get("/trends")
async def get_trends(
    period: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    db: AsyncSession = Depends(get_db),
):
    """Time series: tender count, high-risk count, and total value per week."""
    period_days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    trunc = {"7d": "day", "30d": "week", "90d": "week", "1y": "month"}
    days = period_days[period]
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            func.date_trunc(trunc[period], Tender.date_modified).label("bucket"),
            func.count(Tender.id).label("total"),
            func.count(
                case((Tender.risk_score >= 50, Tender.id), else_=None)
            ).label("high_risk"),
            func.coalesce(func.sum(Tender.expected_value), 0).label("value"),
        )
        .where(Tender.date_modified >= since)
        .group_by("bucket")
        .order_by("bucket")
    )

    rows = result.all()
    return {
        "period": period,
        "tenders": [
            {"date": row.bucket.isoformat(), "count": row.total} for row in rows
        ],
        "high_risk": [
            {"date": row.bucket.isoformat(), "count": row.high_risk} for row in rows
        ],
        "value": [
            {"date": row.bucket.isoformat(), "value": str(row.value)} for row in rows
        ],
    }


@router.get("/cpv-breakdown")
async def get_cpv_breakdown(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Top procurement categories by risk level."""
    result = await db.execute(
        select(
            Tender.cpv_code,
            Tender.cpv_description,
            func.count(Tender.id).label("tender_count"),
            func.avg(Tender.risk_score).label("avg_risk"),
            func.coalesce(func.sum(Tender.expected_value), 0).label("total_value"),
            func.count(case((Tender.risk_score >= 50, Tender.id), else_=None)).label("high_risk_count"),
        )
        .where(Tender.cpv_code.isnot(None))
        .group_by(Tender.cpv_code, Tender.cpv_description)
        .order_by(desc("avg_risk"))
        .limit(limit)
    )

    categories = [
        {
            "cpv_code": row.cpv_code,
            "description": row.cpv_description,
            "tender_count": row.tender_count,
            "avg_risk_score": round(float(row.avg_risk), 2) if row.avg_risk else None,
            "total_value": str(row.total_value),
            "high_risk_count": row.high_risk_count,
        }
        for row in result.all()
    ]
    return {"categories": categories, "total_categories": len(categories)}


@router.get("/top-buyers")
async def get_top_buyers(
    by: str = Query("value", regex="^(value|tenders|risk)$"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Top government buyers by value, tender count, or average risk."""
    order_col = {
        "value": Buyer.total_value.desc().nullslast(),
        "tenders": Buyer.total_tenders.desc().nullslast(),
        "risk": Buyer.avg_competition.asc().nullslast(),  # low competition = higher risk
    }[by]

    result = await db.execute(
        select(Buyer)
        .where(Buyer.total_tenders > 0)
        .order_by(order_col)
        .limit(limit)
    )

    buyers = [
        {
            "id": str(b.id),
            "name": b.name,
            "region": b.region,
            "total_tenders": b.total_tenders,
            "total_value": str(b.total_value) if b.total_value else None,
            "avg_competition": float(b.avg_competition) if b.avg_competition else None,
            "buyer_type": b.buyer_type,
        }
        for b in result.scalars().all()
    ]
    return {"sorted_by": by, "buyers": buyers}


@router.get("/top-contractors")
async def get_top_contractors(
    by: str = Query("value", regex="^(value|wins|risk)$"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Top contractors by value won, win count, or risk score."""
    order_col = {
        "value": Contractor.total_value_won.desc().nullslast(),
        "wins": Contractor.total_wins.desc().nullslast(),
        "risk": Contractor.risk_score.desc().nullslast(),
    }[by]

    result = await db.execute(
        select(Contractor)
        .where(Contractor.total_wins > 0)
        .order_by(order_col)
        .limit(limit)
    )

    from app.schemas import ContractorSummary
    return {
        "sorted_by": by,
        "contractors": [ContractorSummary.model_validate(c) for c in result.scalars().all()],
    }


@router.get("/sync-status")
async def get_sync_status(
    db: AsyncSession = Depends(get_db),
):
    """Data synchronization status from the last completed and running syncs."""
    # Latest completed
    completed = await db.execute(
        select(SyncLog)
        .where(SyncLog.status == "completed")
        .order_by(SyncLog.started_at.desc())
        .limit(1)
    )
    last = completed.scalar_one_or_none()

    # Any currently running
    running = await db.execute(
        select(SyncLog)
        .where(SyncLog.status == "running")
        .order_by(SyncLog.started_at.desc())
        .limit(1)
    )
    active = running.scalar_one_or_none()

    return {
        "last_sync": last.completed_at.isoformat() if last and last.completed_at else None,
        "last_sync_status": last.status if last else "never",
        "records_synced": last.records_created + last.records_updated if last else 0,
        "currently_syncing": active is not None,
        "sync_started_at": active.started_at.isoformat() if active else None,
    }
