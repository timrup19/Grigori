"""
Alerts API endpoints - Red Flag Feed
"""

from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.alert import Alert
from app.models.tender import Tender
from app.models.contractor import Contractor
from app.models.buyer import Buyer
from app.schemas import AlertsResponse, AlertSummary, AlertStats, RiskCategory
from app.api._utils import paginate, alert_to_summary

router = APIRouter()


def _base_alert_query(days: int, min_risk_score: int, risk_category, region):
    """Build base filter list for alert queries."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    filters = [
        Alert.is_active.is_(True),
        Alert.detected_at >= since,
        Alert.risk_score >= min_risk_score,
    ]
    if risk_category:
        filters.append(Alert.risk_category == risk_category.value)
    if region:
        filters.append(Tender.region == region)
    return filters


@router.get("/stats", response_model=AlertStats)
async def get_alert_stats(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate statistics about alerts."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    base = and_(Alert.is_active.is_(True), Alert.detected_at >= since)

    total = await db.scalar(select(func.count(Alert.id)).where(base)) or 0
    critical = await db.scalar(
        select(func.count(Alert.id)).where(base, Alert.risk_category == "critical")
    ) or 0
    high = await db.scalar(
        select(func.count(Alert.id)).where(base, Alert.risk_category == "high")
    ) or 0
    medium = await db.scalar(
        select(func.count(Alert.id)).where(base, Alert.risk_category == "medium")
    ) or 0
    value_at_risk = await db.scalar(
        select(func.coalesce(func.sum(Alert.value_at_risk), 0)).where(base)
    ) or 0

    # By region: join to tender
    region_result = await db.execute(
        select(Tender.region, func.count(Alert.id).label("cnt"))
        .join(Alert, Alert.tender_id == Tender.id)
        .where(base, Tender.region.isnot(None))
        .group_by(Tender.region)
        .order_by(desc("cnt"))
        .limit(10)
    )
    by_region = {row.region: row.cnt for row in region_result.all()}

    # By type
    type_result = await db.execute(
        select(Alert.alert_type, func.count(Alert.id).label("cnt"))
        .where(base)
        .group_by(Alert.alert_type)
    )
    by_type = {row.alert_type: row.cnt for row in type_result.all()}

    return AlertStats(
        total_alerts=total,
        critical_count=critical,
        high_count=high,
        medium_count=medium,
        total_value_at_risk=value_at_risk,
        by_region=by_region,
        by_type=by_type,
    )


@router.get("/latest")
async def get_latest_alerts(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Most recent alerts — for dashboard widgets."""
    result = await db.execute(
        select(Alert)
        .options(
            joinedload(Alert.tender).joinedload(Tender.buyer),
            joinedload(Alert.contractor),
        )
        .where(Alert.is_active.is_(True))
        .order_by(Alert.detected_at.desc())
        .limit(limit)
    )
    alerts = result.unique().scalars().all()
    return {
        "alerts": [alert_to_summary(a) for a in alerts],
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/trending")
async def get_trending_alerts(
    db: AsyncSession = Depends(get_db),
):
    """Trending risk patterns: top regions, CPV categories, contractors."""
    since = datetime.now(timezone.utc) - timedelta(days=7)
    base = and_(Alert.is_active.is_(True), Alert.detected_at >= since)

    region_result = await db.execute(
        select(Tender.region, func.count(Alert.id).label("cnt"))
        .join(Alert, Alert.tender_id == Tender.id)
        .where(base, Tender.region.isnot(None))
        .group_by(Tender.region)
        .order_by(desc("cnt"))
        .limit(5)
    )
    trending_regions = [{"region": r.region, "count": r.cnt} for r in region_result.all()]

    cpv_result = await db.execute(
        select(Tender.cpv_code, Tender.cpv_description, func.count(Alert.id).label("cnt"))
        .join(Alert, Alert.tender_id == Tender.id)
        .where(base, Tender.cpv_code.isnot(None))
        .group_by(Tender.cpv_code, Tender.cpv_description)
        .order_by(desc("cnt"))
        .limit(5)
    )
    trending_categories = [
        {"cpv_code": r.cpv_code, "description": r.cpv_description, "count": r.cnt}
        for r in cpv_result.all()
    ]

    contractor_result = await db.execute(
        select(Contractor.id, Contractor.name, Contractor.edrpou, func.count(Alert.id).label("cnt"))
        .join(Alert, Alert.contractor_id == Contractor.id)
        .where(base)
        .group_by(Contractor.id, Contractor.name, Contractor.edrpou)
        .order_by(desc("cnt"))
        .limit(5)
    )
    frequent_contractors = [
        {"id": str(r.id), "name": r.name, "edrpou": r.edrpou, "alert_count": r.cnt}
        for r in contractor_result.all()
    ]

    return {
        "trending_regions": trending_regions,
        "trending_categories": trending_categories,
        "frequent_contractors": frequent_contractors,
        "period": "7d",
    }


@router.get("/{alert_id}")
async def get_alert_detail(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a specific alert."""
    from uuid import UUID
    try:
        uid = UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID")

    result = await db.execute(
        select(Alert)
        .options(
            joinedload(Alert.tender).joinedload(Tender.buyer),
            joinedload(Alert.contractor),
        )
        .where(Alert.id == uid)
    )
    alert = result.unique().scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert_to_summary(alert)


@router.get("", response_model=AlertsResponse)
async def get_alerts(
    days: int = Query(default=7, ge=1, le=90),
    min_risk_score: int = Query(default=50, ge=0, le=100),
    risk_category: Optional[RiskCategory] = Query(None),
    region: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Red flag feed — high-risk contracts from the past N days."""
    offset = (page - 1) * page_size
    since = datetime.now(timezone.utc) - timedelta(days=days)

    filters = [
        Alert.is_active.is_(True),
        Alert.detected_at >= since,
        Alert.risk_score >= min_risk_score,
    ]
    if risk_category:
        filters.append(Alert.risk_category == risk_category.value)

    # Region filter requires a join to tenders
    if region:
        count_stmt = (
            select(func.count(Alert.id))
            .join(Tender, Alert.tender_id == Tender.id, isouter=True)
            .where(*filters, Tender.region == region)
        )
        data_stmt = (
            select(Alert)
            .join(Tender, Alert.tender_id == Tender.id, isouter=True)
            .options(
                joinedload(Alert.tender).joinedload(Tender.buyer),
                joinedload(Alert.contractor),
            )
            .where(*filters, Tender.region == region)
            .order_by(Alert.detected_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    else:
        count_stmt = select(func.count(Alert.id)).where(*filters)
        data_stmt = (
            select(Alert)
            .options(
                joinedload(Alert.tender).joinedload(Tender.buyer),
                joinedload(Alert.contractor),
            )
            .where(*filters)
            .order_by(Alert.detected_at.desc())
            .offset(offset)
            .limit(page_size)
        )

    total = await db.scalar(count_stmt) or 0
    result = await db.execute(data_stmt)
    alerts = result.unique().scalars().all()

    return AlertsResponse(
        results=[alert_to_summary(a) for a in alerts],
        **paginate(total, page, page_size),
    )
