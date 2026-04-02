"""
Pydantic schemas for API request/response validation.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class RiskCategory(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    TENDER = "tender"
    CONTRACTOR = "contractor"
    NETWORK = "network"


# ============================================================================
# Base Schemas
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Base paginated response."""
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# ============================================================================
# Contractor Schemas
# ============================================================================

class ContractorBase(BaseModel):
    """Base contractor schema."""
    edrpou: str
    name: str
    region: Optional[str] = None


class ContractorSummary(ContractorBase):
    """Contractor summary for search results."""
    id: str
    total_tenders: int = 0
    total_wins: int = 0
    win_rate: Optional[float] = None
    total_value_won: Decimal = Decimal("0")
    risk_score: Optional[float] = None
    risk_category: Optional[RiskCategory] = None
    
    class Config:
        from_attributes = True


class ContractorDetail(ContractorSummary):
    """Full contractor details."""
    address: Optional[str] = None
    is_active: bool = True
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    network_connections: int = 0
    
    # Risk breakdown
    risk_factors: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class ContractorSearchResponse(PaginatedResponse):
    """Paginated contractor search response."""
    results: List[ContractorSummary]


# ============================================================================
# Tender Schemas
# ============================================================================

class TenderBase(BaseModel):
    """Base tender schema."""
    prozorro_id: str
    title: Optional[str] = None
    status: str
    expected_value: Optional[Decimal] = None
    currency: str = "UAH"


class TenderSummary(TenderBase):
    """Tender summary for lists."""
    id: str
    buyer_name: Optional[str] = None
    winner_name: Optional[str] = None
    num_bids: int = 0
    award_value: Optional[Decimal] = None
    region: Optional[str] = None
    cpv_code: Optional[str] = None
    date_modified: Optional[datetime] = None
    
    # Risk
    risk_score: Optional[float] = None
    risk_category: Optional[RiskCategory] = None
    is_single_bidder: bool = False
    is_price_anomaly: bool = False
    
    class Config:
        from_attributes = True


class TenderDetail(TenderSummary):
    """Full tender details."""
    description: Optional[str] = None
    procurement_method: Optional[str] = None
    procurement_method_type: Optional[str] = None
    cpv_description: Optional[str] = None
    award_date: Optional[datetime] = None
    tender_start_date: Optional[datetime] = None
    tender_end_date: Optional[datetime] = None
    
    # Related entities
    buyer_id: Optional[str] = None
    winner_id: Optional[str] = None
    winner_edrpou: Optional[str] = None
    
    # Risk breakdown
    risk_factors: Optional[Dict[str, Any]] = None
    
    # Bids
    bids: Optional[List["BidSummary"]] = None
    
    class Config:
        from_attributes = True


class TenderSearchResponse(PaginatedResponse):
    """Paginated tender search response."""
    results: List[TenderSummary]


# ============================================================================
# Bid Schemas
# ============================================================================

class BidSummary(BaseModel):
    """Bid summary."""
    id: str
    contractor_id: str
    contractor_name: str
    contractor_edrpou: str
    bid_value: Optional[Decimal] = None
    is_winner: bool = False
    
    class Config:
        from_attributes = True


# ============================================================================
# Alert Schemas
# ============================================================================

class AlertSummary(BaseModel):
    """Alert/red flag summary."""
    id: str
    alert_type: AlertType
    risk_score: float
    risk_category: RiskCategory
    reasons: List[str]
    value_at_risk: Optional[Decimal] = None
    detected_at: datetime
    
    # Related tender info
    tender_id: Optional[str] = None
    tender_prozorro_id: Optional[str] = None
    tender_title: Optional[str] = None
    tender_value: Optional[Decimal] = None
    
    # Related contractor info
    contractor_id: Optional[str] = None
    contractor_name: Optional[str] = None
    
    # Buyer info
    buyer_name: Optional[str] = None
    region: Optional[str] = None
    
    class Config:
        from_attributes = True


class AlertsResponse(PaginatedResponse):
    """Paginated alerts response."""
    results: List[AlertSummary]


class AlertStats(BaseModel):
    """Alert statistics."""
    total_alerts: int
    critical_count: int
    high_count: int
    medium_count: int
    total_value_at_risk: Decimal
    by_region: Dict[str, int]
    by_type: Dict[str, int]


# ============================================================================
# Network Schemas
# ============================================================================

class NetworkNode(BaseModel):
    """Node in network graph."""
    id: str
    label: str
    edrpou: str
    risk_score: Optional[float] = None
    risk_category: Optional[RiskCategory] = None
    total_wins: int = 0
    total_value: Decimal = Decimal("0")
    is_center: bool = False  # Is this the searched contractor


class NetworkEdge(BaseModel):
    """Edge in network graph."""
    source: str
    target: str
    weight: int  # Number of co-bids
    suspicion_score: Optional[float] = None


class NetworkGraph(BaseModel):
    """Network graph response."""
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]
    communities: List[List[str]]  # Lists of node IDs forming communities
    total_connections: int
    center_node_id: str


# ============================================================================
# Region Schemas
# ============================================================================

class RegionSummary(BaseModel):
    """Region summary for map."""
    region: str
    latitude: float
    longitude: float
    total_tenders: int = 0
    total_value: Decimal = Decimal("0")
    high_risk_tenders: int = 0
    avg_risk_score: Optional[float] = None
    single_bidder_rate: Optional[float] = None
    
    class Config:
        from_attributes = True


class RegionDetail(RegionSummary):
    """Detailed region information."""
    top_risk_factors: Optional[List[str]] = None
    top_contractors: Optional[List[ContractorSummary]] = None
    recent_alerts: Optional[List[AlertSummary]] = None


# ============================================================================
# Statistics Schemas
# ============================================================================

class OverviewStats(BaseModel):
    """Platform overview statistics."""
    total_tenders: int
    total_contractors: int
    total_value: Decimal
    total_alerts: int
    
    # Risk breakdown
    low_risk_count: int
    medium_risk_count: int
    high_risk_count: int
    critical_risk_count: int
    
    # Rates
    single_bidder_rate: float
    avg_bids_per_tender: float
    
    # Time-based
    last_sync: Optional[datetime] = None
    tenders_last_24h: int = 0
    alerts_last_24h: int = 0


class RiskDistribution(BaseModel):
    """Risk score distribution."""
    buckets: List[Dict[str, Any]]  # {range: "0-10", count: 150}
    mean: float
    median: float
    std: float


# ============================================================================
# Search Schemas
# ============================================================================

class SearchQuery(BaseModel):
    """Search query parameters."""
    q: str = Field(..., min_length=2, description="Search query")
    region: Optional[str] = None
    risk_category: Optional[RiskCategory] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None


class UnifiedSearchResult(BaseModel):
    """Unified search result."""
    type: str  # "contractor", "tender", "buyer"
    id: str
    name: str
    subtitle: Optional[str] = None
    risk_score: Optional[float] = None
    risk_category: Optional[RiskCategory] = None


class UnifiedSearchResponse(BaseModel):
    """Unified search response."""
    query: str
    total: int
    results: List[UnifiedSearchResult]
