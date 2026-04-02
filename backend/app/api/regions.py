"""
Regions API endpoints - Geographic risk heatmap
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.region_stats import RegionStats
from app.models.tender import Tender
from app.models.contractor import Contractor
from app.models.alert import Alert
from app.schemas import RegionSummary, RegionDetail, ContractorSummary, RiskCategory
from app.api._utils import alert_to_summary, tender_to_summary

router = APIRouter()


@router.get("", response_model=List[RegionSummary])
async def get_all_regions(
    db: AsyncSession = Depends(get_db),
):
    """All Ukrainian regions with risk summaries for the heatmap."""
    result = await db.execute(
        select(RegionStats).order_by(RegionStats.avg_risk_score.desc().nullslast())
    )
    regions = result.scalars().all()
    return [RegionSummary.model_validate(r) for r in regions]


@router.get("/summary")
async def get_regions_summary(
    db: AsyncSession = Depends(get_db),
):
    """Aggregate summary across all regions — for dashboard overview."""
    total = await db.scalar(select(func.count(RegionStats.id))) or 0

    critical_result = await db.execute(
        select(RegionStats.region)
        .where(RegionStats.avg_risk_score >= 75)
    )
    critical_regions = [row.region for row in critical_result.all()]

    highest_result = await db.execute(
        select(RegionStats)
        .where(RegionStats.avg_risk_score.isnot(None))
        .order_by(RegionStats.avg_risk_score.desc())
        .limit(1)
    )
    highest = highest_result.scalar_one_or_none()

    total_value = await db.scalar(
        select(func.coalesce(func.sum(RegionStats.total_value), 0))
    ) or 0

    return {
        "total_regions": total,
        "regions_with_critical_alerts": len(critical_regions),
        "critical_regions": critical_regions,
        "highest_risk_region": highest.region if highest else None,
        "highest_risk_score": float(highest.avg_risk_score) if highest and highest.avg_risk_score else None,
        "total_value_monitored": str(total_value),
    }


@router.get("/{region_name}", response_model=RegionDetail)
async def get_region_detail(
    region_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Detailed region info: stats, top contractors, recent alerts."""
    result = await db.execute(
        select(RegionStats).where(RegionStats.region == region_name)
    )
    region = result.scalar_one_or_none()
    if not region:
        raise HTTPException(status_code=404, detail=f"Region '{region_name}' not found")

    # Top contractors in region by risk score
    c_result = await db.execute(
        select(Contractor)
        .where(Contractor.region == region_name)
        .order_by(Contractor.risk_score.desc().nullslast())
        .limit(5)
    )
    top_contractors = [ContractorSummary.model_validate(c) for c in c_result.scalars().all()]

    # Recent high-risk alerts for tenders in this region
    a_result = await db.execute(
        select(Alert)
        .join(Tender, Alert.tender_id == Tender.id)
        .options(
            joinedload(Alert.tender).joinedload(Tender.buyer),
            joinedload(Alert.contractor),
        )
        .where(Alert.is_active.is_(True), Tender.region == region_name)
        .order_by(Alert.detected_at.desc())
        .limit(5)
    )
    recent_alerts = [alert_to_summary(a) for a in a_result.unique().scalars().all()]

    top_risk_factors = region.top_risk_factors or []

    return RegionDetail(
        region=region.region,
        latitude=float(region.latitude) if region.latitude else 0.0,
        longitude=float(region.longitude) if region.longitude else 0.0,
        total_tenders=region.total_tenders or 0,
        total_value=region.total_value or 0,
        high_risk_tenders=region.high_risk_tenders or 0,
        avg_risk_score=float(region.avg_risk_score) if region.avg_risk_score else None,
        single_bidder_rate=float(region.single_bidder_rate) if region.single_bidder_rate else None,
        top_risk_factors=top_risk_factors,
        top_contractors=top_contractors,
        recent_alerts=recent_alerts,
    )


@router.get("/{region_name}/tenders")
async def get_region_tenders(
    region_name: str,
    risk_category: Optional[RiskCategory] = Query(None),
    days: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Tenders in a specific region, optionally filtered by risk and time window."""
    from datetime import datetime, timedelta, timezone
    from app.api._utils import paginate

    offset = (page - 1) * page_size
    since = datetime.now(timezone.utc) - timedelta(days=days)

    filters = [Tender.region == region_name, Tender.date_modified >= since]
    if risk_category:
        filters.append(Tender.risk_category == risk_category.value)

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

    return {
        "region": region_name,
        **paginate(total, page, page_size),
        "results": [tender_to_summary(t) for t in tenders],
    }


@router.get("/{region_name}/contractors")
async def get_region_contractors(
    region_name: str,
    min_risk_score: int = Query(0, ge=0, le=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Contractors operating in a region."""
    from app.api._utils import paginate

    offset = (page - 1) * page_size
    where = and_(
        Contractor.region == region_name,
        Contractor.risk_score >= min_risk_score,
    )

    total = await db.scalar(select(func.count(Contractor.id)).where(where)) or 0
    result = await db.execute(
        select(Contractor)
        .where(where)
        .order_by(Contractor.risk_score.desc().nullslast())
        .offset(offset)
        .limit(page_size)
    )
    contractors = result.scalars().all()

    return {
        "region": region_name,
        **paginate(total, page, page_size),
        "results": [ContractorSummary.model_validate(c) for c in contractors],
    }


@router.get("/{region_name}/trends")
async def get_region_trends(
    region_name: str,
    period: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    db: AsyncSession = Depends(get_db),
):
    """Risk score trend over time for a region (weekly buckets)."""
    from datetime import datetime, timedelta, timezone

    period_days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    days = period_days[period]
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            func.date_trunc("week", Tender.date_modified).label("week"),
            func.count(Tender.id).label("total"),
            func.avg(Tender.risk_score).label("avg_risk"),
            func.sum(Tender.expected_value).label("total_value"),
        )
        .where(Tender.region == region_name, Tender.date_modified >= since)
        .group_by("week")
        .order_by("week")
    )

    data_points = [
        {
            "week": row.week.isoformat() if row.week else None,
            "total_tenders": row.total,
            "avg_risk_score": float(row.avg_risk) if row.avg_risk else None,
            "total_value": str(row.total_value) if row.total_value else None,
        }
        for row in result.all()
    ]

    return {"region": region_name, "period": period, "data_points": data_points}
