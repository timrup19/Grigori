"""
Statistics API endpoints - Platform-wide metrics
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import OverviewStats, RiskDistribution

router = APIRouter()


@router.get("/overview", response_model=OverviewStats)
async def get_overview_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get platform-wide overview statistics.
    
    This powers the main dashboard - showing:
    - Total tenders and contractors monitored
    - Total value under surveillance
    - Risk breakdown by category
    - Recent activity metrics
    """
    # TODO: Implement aggregation queries
    
    return OverviewStats(
        total_tenders=0,
        total_contractors=0,
        total_value=0,
        total_alerts=0,
        low_risk_count=0,
        medium_risk_count=0,
        high_risk_count=0,
        critical_risk_count=0,
        single_bidder_rate=0.0,
        avg_bids_per_tender=0.0,
        last_sync=None,
        tenders_last_24h=0,
        alerts_last_24h=0
    )


@router.get("/risk-distribution", response_model=RiskDistribution)
async def get_risk_distribution(
    db: AsyncSession = Depends(get_db)
):
    """
    Get risk score distribution across all tenders.
    
    Returns histogram buckets for charting.
    """
    # TODO: Implement histogram query
    
    return RiskDistribution(
        buckets=[
            {"range": "0-10", "count": 0},
            {"range": "11-20", "count": 0},
            {"range": "21-30", "count": 0},
            {"range": "31-40", "count": 0},
            {"range": "41-50", "count": 0},
            {"range": "51-60", "count": 0},
            {"range": "61-70", "count": 0},
            {"range": "71-80", "count": 0},
            {"range": "81-90", "count": 0},
            {"range": "91-100", "count": 0},
        ],
        mean=0.0,
        median=0.0,
        std=0.0
    )


@router.get("/trends")
async def get_trends(
    period: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get trends over time.
    
    Returns time series data for:
    - Total tenders per day/week
    - High-risk tenders per day/week
    - Total value per day/week
    """
    # TODO: Implement time series aggregation
    
    return {
        "period": period,
        "tenders": [],
        "high_risk": [],
        "value": []
    }


@router.get("/cpv-breakdown")
async def get_cpv_breakdown(
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Get breakdown by procurement category (CPV code).
    
    Shows which sectors have the most risk.
    """
    # TODO: Implement groupby CPV
    
    return {
        "categories": [],
        "total_categories": 0
    }


@router.get("/top-buyers")
async def get_top_buyers(
    by: str = Query("value", regex="^(value|tenders|risk)$"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top government buyers by value, tender count, or risk.
    """
    # TODO: Implement
    
    return {
        "sorted_by": by,
        "buyers": []
    }


@router.get("/top-contractors")
async def get_top_contractors(
    by: str = Query("value", regex="^(value|wins|risk)$"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top contractors by value won, win count, or risk score.
    """
    # TODO: Implement
    
    return {
        "sorted_by": by,
        "contractors": []
    }


@router.get("/sync-status")
async def get_sync_status(
    db: AsyncSession = Depends(get_db)
):
    """
    Get data synchronization status.
    
    Shows when data was last synced from Prozorro API.
    """
    # TODO: Query sync_log table
    
    return {
        "last_sync": None,
        "last_sync_status": "unknown",
        "records_synced": 0,
        "next_sync": None
    }
