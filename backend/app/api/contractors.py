"""
Contractors API endpoints - Company profiles and details
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ContractorDetail, ContractorSummary, 
    TenderSummary, NetworkGraph, RiskCategory
)

router = APIRouter()


@router.get("/{contractor_id}", response_model=ContractorDetail)
async def get_contractor(
    contractor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed profile for a contractor.
    
    Includes:
    - Company information (name, EDRPOU, region)
    - Win statistics (total tenders, wins, value)
    - Risk score and breakdown
    - Network connection count
    
    This is the main "Contractor Profile" view.
    """
    # TODO: Implement database query
    
    raise HTTPException(status_code=404, detail="Contractor not found")


@router.get("/{contractor_id}/tenders")
async def get_contractor_tenders(
    contractor_id: str,
    status: Optional[str] = Query(None, description="Filter by tender status"),
    won_only: bool = Query(False, description="Only show won tenders"),
    risk_category: Optional[RiskCategory] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get tender history for a contractor.
    
    Shows all tenders this company has bid on, with option
    to filter to only wins.
    """
    # TODO: Implement
    
    return {
        "contractor_id": contractor_id,
        "total": 0,
        "page": page,
        "page_size": page_size,
        "results": []
    }


@router.get("/{contractor_id}/network", response_model=NetworkGraph)
async def get_contractor_network(
    contractor_id: str,
    depth: int = Query(2, ge=1, le=3),
    max_nodes: int = Query(50, ge=10, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get co-bidding network for a contractor.
    
    Alias for /api/network/{contractor_id}
    Included here for REST consistency.
    """
    # TODO: Call network router logic
    
    return NetworkGraph(
        nodes=[],
        edges=[],
        communities=[],
        total_connections=0,
        center_node_id=contractor_id
    )


@router.get("/{contractor_id}/risk-factors")
async def get_contractor_risk_factors(
    contractor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed risk breakdown for a contractor.
    
    Shows each risk signal and its contribution
    to the overall score.
    """
    # TODO: Implement
    
    return {
        "contractor_id": contractor_id,
        "risk_score": 0,
        "risk_category": "low",
        "factors": {
            "price_anomaly": {"score": 0, "description": ""},
            "bid_pattern": {"score": 0, "description": ""},
            "single_bidder": {"score": 0, "description": ""},
            "network_risk": {"score": 0, "description": ""},
            "high_value": {"score": 0, "description": ""}
        },
        "red_flags": []
    }


@router.get("/{contractor_id}/buyers")
async def get_contractor_buyers(
    contractor_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get government buyers this contractor has worked with.
    
    Sorted by frequency of contracts.
    """
    # TODO: Implement
    
    return {
        "contractor_id": contractor_id,
        "buyers": [],
        "total": 0
    }


@router.get("/{contractor_id}/timeline")
async def get_contractor_timeline(
    contractor_id: str,
    period: str = Query("1y", regex="^(3m|6m|1y|all)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get activity timeline for a contractor.
    
    Shows tenders and wins over time for visualization.
    """
    # TODO: Implement time series
    
    return {
        "contractor_id": contractor_id,
        "period": period,
        "bids": [],
        "wins": [],
        "risk_over_time": []
    }


@router.get("/by-edrpou/{edrpou}")
async def get_contractor_by_edrpou(
    edrpou: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Look up contractor by Ukrainian company registration number (EDRPOU).
    """
    # TODO: Implement
    
    raise HTTPException(status_code=404, detail=f"Contractor with EDRPOU {edrpou} not found")


@router.get("/high-risk", response_model=List[ContractorSummary])
async def get_high_risk_contractors(
    min_risk_score: int = Query(50, ge=0, le=100),
    min_wins: int = Query(1, ge=0),
    region: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get contractors with elevated risk scores.
    
    Useful for identifying companies that warrant investigation.
    """
    # TODO: Implement
    
    return []
