"""Shared helpers for converting ORM objects to Pydantic schemas."""

import math
from decimal import Decimal
from app.models.tender import Tender
from app.models.alert import Alert
from app.schemas import TenderSummary, AlertSummary


def paginate(total: int, page: int, page_size: int) -> dict:
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return dict(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


def tender_to_summary(t: Tender) -> TenderSummary:
    return TenderSummary(
        id=str(t.id),
        prozorro_id=t.prozorro_id,
        title=t.title,
        status=t.status or "unknown",
        expected_value=t.expected_value,
        currency=t.currency or "UAH",
        buyer_name=t.buyer.name if t.buyer else None,
        winner_name=t.winner.name if t.winner else None,
        num_bids=t.num_bids or 0,
        award_value=t.award_value,
        region=t.region,
        cpv_code=t.cpv_code,
        date_modified=t.date_modified,
        risk_score=float(t.risk_score) if t.risk_score is not None else None,
        risk_category=t.risk_category,
        is_single_bidder=t.is_single_bidder or False,
        is_price_anomaly=t.is_price_anomaly or False,
    )


def alert_to_summary(a: Alert) -> AlertSummary:
    tender = a.tender
    contractor = a.contractor
    buyer = tender.buyer if tender else None
    return AlertSummary(
        id=str(a.id),
        alert_type=a.alert_type,
        risk_score=float(a.risk_score),
        risk_category=a.risk_category,
        reasons=a.reasons or [],
        value_at_risk=a.value_at_risk,
        detected_at=a.detected_at,
        tender_id=str(tender.id) if tender else None,
        tender_prozorro_id=tender.prozorro_id if tender else None,
        tender_title=tender.title if tender else None,
        tender_value=tender.expected_value if tender else None,
        contractor_id=str(contractor.id) if contractor else None,
        contractor_name=contractor.name if contractor else None,
        buyer_name=buyer.name if buyer else None,
        region=tender.region if tender else None,
    )
