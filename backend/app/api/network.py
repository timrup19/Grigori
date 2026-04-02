"""
Network API endpoints - Co-bidding graph visualization
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc

from app.database import get_db
from app.models.contractor import Contractor
from app.models.co_bidding import CoBidding
from app.schemas import NetworkGraph, NetworkNode, NetworkEdge

router = APIRouter()


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid contractor ID: {value}")


async def build_network_graph(
    contractor_id: str,
    depth: int,
    max_nodes: int,
    db: AsyncSession,
) -> NetworkGraph:
    """
    BFS co-bidding graph starting from contractor_id up to `depth` hops.
    Respects max_nodes cap.
    """
    center_uuid = _parse_uuid(contractor_id)

    visited: set[UUID] = {center_uuid}
    frontier: set[UUID] = {center_uuid}
    all_edges: dict[UUID, CoBidding] = {}

    for _ in range(depth):
        if not frontier or len(visited) >= max_nodes:
            break

        result = await db.execute(
            select(CoBidding).where(
                or_(
                    CoBidding.contractor_a_id.in_(frontier),
                    CoBidding.contractor_b_id.in_(frontier),
                )
            )
        )
        edges = result.scalars().all()

        new_frontier: set[UUID] = set()
        for edge in edges:
            all_edges[edge.id] = edge
            for nid in (edge.contractor_a_id, edge.contractor_b_id):
                if nid not in visited:
                    new_frontier.add(nid)
                    if len(visited) + len(new_frontier) >= max_nodes:
                        break
            if len(visited) + len(new_frontier) >= max_nodes:
                break

        visited.update(new_frontier)
        frontier = new_frontier

    # Fetch contractor details for all nodes
    c_result = await db.execute(
        select(Contractor).where(Contractor.id.in_(visited))
    )
    contractors = {c.id: c for c in c_result.scalars().all()}

    nodes = [
        NetworkNode(
            id=str(cid),
            label=contractors[cid].name if cid in contractors else str(cid),
            edrpou=contractors[cid].edrpou if cid in contractors else "",
            risk_score=float(contractors[cid].risk_score) if cid in contractors and contractors[cid].risk_score is not None else None,
            risk_category=contractors[cid].risk_category if cid in contractors else None,
            total_wins=contractors[cid].total_wins if cid in contractors else 0,
            total_value=contractors[cid].total_value_won if cid in contractors else 0,
            is_center=(cid == center_uuid),
        )
        for cid in visited
    ]

    # Only include edges where both endpoints are in our node set
    edges = [
        NetworkEdge(
            source=str(e.contractor_a_id),
            target=str(e.contractor_b_id),
            weight=e.co_bid_count,
            suspicion_score=float(e.suspicion_score) if e.suspicion_score is not None else None,
        )
        for e in all_edges.values()
        if e.contractor_a_id in visited and e.contractor_b_id in visited
    ]

    return NetworkGraph(
        nodes=nodes,
        edges=edges,
        communities=[],  # Community detection is CPU-heavy; done offline
        total_connections=len(edges),
        center_node_id=contractor_id,
    )


# ── fixed-path routes first ────────────────────────────────────────────────────

@router.get("/stats")
async def get_network_stats(
    db: AsyncSession = Depends(get_db),
):
    """Overall network statistics."""
    total_nodes = await db.scalar(select(func.count(Contractor.id))) or 0
    total_edges = await db.scalar(select(func.count(CoBidding.id))) or 0
    avg_degree = (2 * total_edges / total_nodes) if total_nodes else 0.0

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "avg_degree": round(avg_degree, 2),
        "num_communities": 0,  # requires offline graph analysis
        "largest_community_size": 0,
    }


@router.get("/pairs/top")
async def get_top_co_bidding_pairs(
    min_co_bids: int = Query(5, ge=2),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Top co-bidding pairs by frequency — potential collusion signals."""
    result = await db.execute(
        select(CoBidding)
        .where(CoBidding.co_bid_count >= min_co_bids)
        .order_by(CoBidding.co_bid_count.desc())
        .limit(limit)
    )
    pairs_orm = result.scalars().all()

    # Fetch contractor names in bulk
    all_ids = set()
    for p in pairs_orm:
        all_ids.update([p.contractor_a_id, p.contractor_b_id])

    contractors = {}
    if all_ids:
        c_result = await db.execute(
            select(Contractor.id, Contractor.name, Contractor.edrpou).where(
                Contractor.id.in_(all_ids)
            )
        )
        for row in c_result.all():
            contractors[row.id] = {"name": row.name, "edrpou": row.edrpou}

    pairs = [
        {
            "contractor_a": {
                "id": str(p.contractor_a_id),
                **contractors.get(p.contractor_a_id, {}),
            },
            "contractor_b": {
                "id": str(p.contractor_b_id),
                **contractors.get(p.contractor_b_id, {}),
            },
            "co_bid_count": p.co_bid_count,
            "suspicion_score": float(p.suspicion_score) if p.suspicion_score is not None else None,
            "last_co_bid_date": p.last_co_bid_date.isoformat() if p.last_co_bid_date else None,
        }
        for p in pairs_orm
    ]
    return {"pairs": pairs, "total": len(pairs)}


@router.get("/communities/suspicious")
async def get_suspicious_communities(
    min_size: int = Query(3, ge=2),
    min_value: float = Query(1_000_000, description="Minimum total value won"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Groups of contractors with high suspicion scores on their co-bidding edges.
    Uses a simple threshold approach (full community detection runs offline).
    """
    # Find contractors involved in multiple high-suspicion co-bidding pairs
    result = await db.execute(
        select(
            CoBidding.contractor_a_id.label("cid"),
            func.count(CoBidding.id).label("pair_count"),
            func.avg(CoBidding.suspicion_score).label("avg_suspicion"),
        )
        .where(CoBidding.suspicion_score >= 60)
        .group_by(CoBidding.contractor_a_id)
        .having(func.count(CoBidding.id) >= min_size - 1)
        .order_by(desc("avg_suspicion"))
        .limit(limit)
    )
    rows = result.all()

    center_ids = [row.cid for row in rows]
    contractors = {}
    if center_ids:
        c_result = await db.execute(
            select(Contractor).where(Contractor.id.in_(center_ids))
        )
        for c in c_result.scalars().all():
            contractors[c.id] = c

    communities = [
        {
            "center_id": str(row.cid),
            "center_name": contractors[row.cid].name if row.cid in contractors else None,
            "members": row.pair_count + 1,
            "avg_suspicion_score": float(row.avg_suspicion) if row.avg_suspicion else None,
        }
        for row in rows
    ]
    return {"communities": communities, "total": len(communities)}


# ── parameterized routes ────────────────────────────────────────────────────────

@router.get("/{contractor_id}", response_model=NetworkGraph)
async def get_contractor_network(
    contractor_id: str,
    depth: int = Query(2, ge=1, le=3),
    max_nodes: int = Query(50, ge=10, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Co-bidding network centered on a contractor.
    Returns nodes (companies) and edges (co-bidding relationships).
    """
    return await build_network_graph(contractor_id, depth, max_nodes, db)


@router.get("/{contractor_id}/connections")
async def get_contractor_connections(
    contractor_id: str,
    min_co_bids: int = Query(2, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Direct co-bidders for a contractor, sorted by frequency."""
    uid = _parse_uuid(contractor_id)

    result = await db.execute(
        select(CoBidding)
        .where(
            and_(
                or_(
                    CoBidding.contractor_a_id == uid,
                    CoBidding.contractor_b_id == uid,
                ),
                CoBidding.co_bid_count >= min_co_bids,
            )
        )
        .order_by(CoBidding.co_bid_count.desc())
        .limit(limit)
    )
    pairs = result.scalars().all()

    peer_ids = [
        p.contractor_b_id if p.contractor_a_id == uid else p.contractor_a_id
        for p in pairs
    ]
    contractors = {}
    if peer_ids:
        c_result = await db.execute(
            select(Contractor).where(Contractor.id.in_(peer_ids))
        )
        for c in c_result.scalars().all():
            contractors[c.id] = c

    connections = []
    for p in pairs:
        peer_id = p.contractor_b_id if p.contractor_a_id == uid else p.contractor_a_id
        c = contractors.get(peer_id)
        connections.append({
            "contractor_id": str(peer_id),
            "name": c.name if c else None,
            "edrpou": c.edrpou if c else None,
            "risk_score": float(c.risk_score) if c and c.risk_score is not None else None,
            "co_bid_count": p.co_bid_count,
            "suspicion_score": float(p.suspicion_score) if p.suspicion_score is not None else None,
        })

    return {"contractor_id": contractor_id, "connections": connections, "total": len(connections)}
