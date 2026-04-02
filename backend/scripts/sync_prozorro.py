#!/usr/bin/env python3
"""
sync_prozorro.py

Fetches procurement data from Ukraine's Prozorro public API, persists it to
PostgreSQL, then runs risk scoring and builds the co-bidding network.

Usage:
    python scripts/sync_prozorro.py               # sync 1000 tenders
    python scripts/sync_prozorro.py --count 500   # sync 500 tenders
    python scripts/sync_prozorro.py --dry-run     # fetch & score without saving
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import pandas as pd
from sqlalchemy import select, update, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

# ── path setup so we can import app.* ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal, engine
from app.models.contractor import Contractor
from app.models.buyer import Buyer
from app.models.tender import Tender
from app.models.bid import Bid
from app.models.co_bidding import CoBidding
from app.models.alert import Alert
from app.models.region_stats import RegionStats
from app.models.sync_log import SyncLog
from app.services.prozorro_client import ProzorroClient
from app.services.risk_engine import RiskScoringEngine
from app.services.network_analyzer import NetworkAnalyzer


# ── helpers ────────────────────────────────────────────────────────────────────

def parse_dt(s: Optional[str]) -> Optional[datetime]:
    """Parse ISO-8601 datetime string → aware datetime."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def parse_date(s: Optional[str]):
    """Parse date-only string."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s[:10]).date()
    except Exception:
        return None


# ── main syncer class ──────────────────────────────────────────────────────────

class ProzorroSyncer:
    """Orchestrates the full sync: fetch → parse → persist → score → alerts."""

    def __init__(self, db: AsyncSession, dry_run: bool = False):
        self.db = db
        self.dry_run = dry_run
        self.client = ProzorroClient()
        self.risk_engine = RiskScoringEngine()
        self.network_analyzer = NetworkAnalyzer()

        # ID mapping caches (populated during upsert phase)
        self.edrpou_to_uuid: Dict[str, UUID] = {}        # EDRPOU → contractor UUID
        self.prozorro_to_buyer_uuid: Dict[str, UUID] = {}  # prozorro_id → buyer UUID
        self.prozorro_to_tender_uuid: Dict[str, UUID] = {} # prozorro_id → tender UUID

        self.stats = {
            "tenders_fetched": 0,
            "tenders_created": 0,
            "tenders_updated": 0,
            "contractors_created": 0,
            "buyers_created": 0,
            "bids_created": 0,
            "alerts_created": 0,
            "errors": 0,
        }

    # ── public entry point ──────────────────────────────────────────────────────

    async def run(self, count: int = 1000) -> Dict:
        log_entry = await self._start_sync_log()
        try:
            # 1. Fetch
            raw_tenders = await self._fetch_tenders(count)
            self.stats["tenders_fetched"] = len(raw_tenders)

            # 2. Parse
            parsed = self.client.parse_tenders_batch(raw_tenders)
            logger.info(f"Parsed {len(parsed)} valid tenders")

            if not parsed:
                logger.warning("No valid tenders to process")
                await self._finish_sync_log(log_entry, success=True)
                return self.stats

            # 3. Upsert entities (buyers, contractors)
            await self._upsert_entities(parsed)

            # 4. Upsert tenders + bids
            await self._upsert_tenders(parsed)
            await self.db.commit()

            # 5. Risk scoring (CPU-heavy — run in thread executor)
            scored_df = await self._run_risk_scoring(parsed)

            # 6. Persist risk scores back to DB
            await self._persist_risk_scores(scored_df)
            await self.db.commit()

            # 7. Build + persist co-bidding network
            await self._update_co_bidding_network(parsed)
            await self.db.commit()

            # 8. Update contractor aggregate stats
            await self._update_contractor_stats()
            await self.db.commit()

            # 9. Refresh region stats
            await self._update_region_stats()
            await self.db.commit()

            # 10. Create alerts for high-risk tenders
            await self._create_alerts(scored_df)
            await self.db.commit()

            await self._finish_sync_log(log_entry, success=True)
            self._print_summary()
            return self.stats

        except Exception as exc:
            logger.exception(f"Sync failed: {exc}")
            self.stats["errors"] += 1
            await self.db.rollback()
            await self._finish_sync_log(log_entry, success=False, error=str(exc))
            raise
        finally:
            await self.client.close()

    # ── step 1: fetch ───────────────────────────────────────────────────────────

    async def _fetch_tenders(self, count: int) -> List[Dict]:
        logger.info(f"Fetching {count} tenders from Prozorro API...")

        # Get the IDs list first
        list_resp = await self.client.get_tenders(
            limit=min(count * 2, 1000), descending=True
        )
        if not list_resp or "data" not in list_resp:
            raise RuntimeError("Failed to fetch tender list from Prozorro API")

        tender_ids = [t["id"] for t in list_resp["data"] if t.get("id")]
        tender_ids = tender_ids[:count]
        logger.info(f"Got {len(tender_ids)} tender IDs — fetching details...")

        # Fetch details concurrently (5 at a time to be polite to the API)
        semaphore = asyncio.Semaphore(5)

        async def fetch_one(tid: str) -> Optional[Dict]:
            async with semaphore:
                resp = await self.client.get_tender_details(tid)
                if resp and "data" in resp:
                    return resp["data"]
                return None

        results = await asyncio.gather(
            *[fetch_one(tid) for tid in tender_ids], return_exceptions=False
        )
        tenders = [r for r in results if r is not None]
        logger.info(f"Successfully fetched details for {len(tenders)} tenders")
        return tenders

    # ── step 3: upsert buyers + contractors ────────────────────────────────────

    async def _upsert_entities(self, parsed: List[Dict]) -> None:
        logger.info("Upserting buyers and contractors...")
        buyers_seen: Dict[str, dict] = {}
        contractors_seen: Dict[str, dict] = {}

        for t in parsed:
            # Buyers
            bid_key = t.get("buyer_id", "")
            if bid_key and bid_key not in buyers_seen:
                buyers_seen[bid_key] = {
                    "prozorro_id": bid_key,
                    "name": t.get("buyer_name", "Unknown"),
                    "region": t.get("buyer_region"),
                }

            # Winner as contractor
            edrpou = t.get("winner_id", "")
            name = t.get("winner_name", "")
            if edrpou and name and edrpou not in contractors_seen:
                contractors_seen[edrpou] = {"edrpou": edrpou, "name": name}

            # All bidders as contractors
            for eid, ename in zip(t.get("bidder_ids", []), t.get("bidder_names", [])):
                if eid and eid not in contractors_seen:
                    contractors_seen[eid] = {"edrpou": eid, "name": ename}

        # Bulk upsert buyers
        for buyer_data in buyers_seen.values():
            uuid = await self._upsert_buyer(buyer_data)
            if uuid:
                self.prozorro_to_buyer_uuid[buyer_data["prozorro_id"]] = uuid

        logger.info(f"Upserted {len(buyers_seen)} buyers")

        # Bulk upsert contractors
        for c_data in contractors_seen.values():
            uuid = await self._upsert_contractor(c_data)
            if uuid:
                self.edrpou_to_uuid[c_data["edrpou"]] = uuid

        logger.info(f"Upserted {len(contractors_seen)} contractors")

    async def _upsert_buyer(self, data: dict) -> Optional[UUID]:
        if self.dry_run:
            return None
        stmt = (
            pg_insert(Buyer)
            .values(
                prozorro_id=data["prozorro_id"],
                name=data["name"],
                name_normalized=data["name"].lower(),
                region=data.get("region"),
            )
            .on_conflict_do_update(
                index_elements=["prozorro_id"],
                set_={"name": data["name"], "region": data.get("region")},
            )
            .returning(Buyer.id)
        )
        result = await self.db.execute(stmt)
        row = result.fetchone()
        self.stats["buyers_created"] += 1
        return row[0] if row else None

    async def _upsert_contractor(self, data: dict) -> Optional[UUID]:
        if self.dry_run:
            return None
        stmt = (
            pg_insert(Contractor)
            .values(
                edrpou=data["edrpou"],
                name=data["name"],
                region=data.get("region"),
                is_active=True,
                first_seen_at=datetime.now(timezone.utc),
                last_seen_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_update(
                index_elements=["edrpou"],
                set_={
                    "name": data["name"],
                    "last_seen_at": datetime.now(timezone.utc),
                },
            )
            .returning(Contractor.id)
        )
        result = await self.db.execute(stmt)
        row = result.fetchone()
        self.stats["contractors_created"] += 1
        return row[0] if row else None

    # ── step 4: upsert tenders + bids ──────────────────────────────────────────

    async def _upsert_tenders(self, parsed: List[Dict]) -> None:
        logger.info(f"Upserting {len(parsed)} tenders and their bids...")

        for t in parsed:
            buyer_uuid = self.prozorro_to_buyer_uuid.get(t.get("buyer_id", ""))
            winner_uuid = self.edrpou_to_uuid.get(t.get("winner_id", ""))

            tender_uuid = await self._upsert_tender(t, buyer_uuid, winner_uuid)
            if tender_uuid:
                self.prozorro_to_tender_uuid[t["prozorro_id"]] = tender_uuid
                await self._upsert_bids(tender_uuid, t)

    async def _upsert_tender(
        self,
        t: dict,
        buyer_uuid: Optional[UUID],
        winner_uuid: Optional[UUID],
    ) -> Optional[UUID]:
        if self.dry_run:
            return None

        values = dict(
            prozorro_id=t["prozorro_id"],
            title=t.get("title"),
            description=t.get("description"),
            status=t.get("status", "unknown"),
            procurement_method=t.get("procurement_method"),
            procurement_method_type=t.get("procurement_method_type"),
            expected_value=t.get("expected_value"),
            currency=t.get("currency", "UAH"),
            cpv_code=t.get("cpv_code"),
            cpv_description=t.get("cpv_description"),
            buyer_id=buyer_uuid,
            winner_id=winner_uuid,
            award_value=t.get("award_amount"),
            award_date=parse_date(t.get("award_date")),
            num_bids=t.get("num_bids", 0),
            tender_start_date=parse_dt(t.get("start_date")),
            tender_end_date=parse_dt(t.get("end_date")),
            date_modified=parse_dt(t.get("date_modified")),
            region=t.get("buyer_region"),
            is_single_bidder=t.get("num_bids", 0) <= 1,
            raw_data=t.get("raw_data"),
        )

        stmt = (
            pg_insert(Tender)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["prozorro_id"],
                set_={k: v for k, v in values.items() if k != "prozorro_id"},
            )
            .returning(Tender.id)
        )
        result = await self.db.execute(stmt)
        row = result.fetchone()
        if row:
            self.stats["tenders_created"] += 1
        return row[0] if row else None

    async def _upsert_bids(self, tender_uuid: UUID, t: dict) -> None:
        if self.dry_run:
            return

        bidder_ids = t.get("bidder_ids", [])
        bidder_names = t.get("bidder_names", [])
        bid_amounts = t.get("bid_amounts", [])
        winner_edrpou = t.get("winner_id", "")

        for i, edrpou in enumerate(bidder_ids):
            contractor_uuid = self.edrpou_to_uuid.get(edrpou)
            if not contractor_uuid:
                continue

            bid_val = bid_amounts[i] if i < len(bid_amounts) else None
            is_win = edrpou == winner_edrpou

            stmt = (
                pg_insert(Bid)
                .values(
                    tender_id=tender_uuid,
                    contractor_id=contractor_uuid,
                    bid_value=bid_val,
                    currency=t.get("currency", "UAH"),
                    status="active",
                    is_winner=is_win,
                )
                .on_conflict_do_update(
                    constraint="idx_bids_unique",
                    set_={"bid_value": bid_val, "is_winner": is_win},
                )
            )
            await self.db.execute(stmt)
            self.stats["bids_created"] += 1

    # ── step 5: risk scoring ────────────────────────────────────────────────────

    async def _run_risk_scoring(self, parsed: List[Dict]) -> pd.DataFrame:
        logger.info("Running risk scoring engine...")
        df = pd.DataFrame(parsed)

        loop = asyncio.get_event_loop()
        scored_df = await loop.run_in_executor(
            None, self.risk_engine.score_tenders, df
        )
        return scored_df

    # ── step 6: persist risk scores ────────────────────────────────────────────

    async def _persist_risk_scores(self, df: pd.DataFrame) -> None:
        if self.dry_run:
            return

        logger.info("Persisting risk scores to DB...")
        now = datetime.now(timezone.utc)

        for _, row in df.iterrows():
            tender_uuid = self.prozorro_to_tender_uuid.get(row["prozorro_id"])
            if not tender_uuid:
                continue

            await self.db.execute(
                update(Tender)
                .where(Tender.id == tender_uuid)
                .values(
                    risk_score=float(row.get("risk_score", 0)),
                    risk_category=row.get("risk_category", "low"),
                    risk_factors=row.get("risk_factors"),
                    is_single_bidder=bool(row.get("is_single_bidder", False)),
                    is_price_anomaly=bool(row.get("is_price_anomaly", False)),
                    is_bid_pattern_anomaly=bool(row.get("is_bid_pattern_anomaly", False)),
                    risk_updated_at=now,
                )
            )

    # ── step 7: co-bidding network ─────────────────────────────────────────────

    async def _update_co_bidding_network(self, parsed: List[Dict]) -> None:
        if self.dry_run:
            return

        logger.info("Building co-bidding network...")
        df = pd.DataFrame(parsed)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, self.network_analyzer.build_co_bidding_network, df, 2
        )
        await loop.run_in_executor(None, self.network_analyzer.calculate_metrics)

        pairs = self.network_analyzer.get_co_bidding_pairs(min_co_bids=2, limit=5000)
        logger.info(f"Found {len(pairs)} co-bidding pairs with 2+ shared tenders")

        now = datetime.now(timezone.utc)
        for pair in pairs:
            a_uuid = self.edrpou_to_uuid.get(pair["contractor_a_id"])
            b_uuid = self.edrpou_to_uuid.get(pair["contractor_b_id"])
            if not a_uuid or not b_uuid or a_uuid == b_uuid:
                continue

            # Enforce the CHECK constraint: a < b (lexicographic on UUID string)
            if str(a_uuid) > str(b_uuid):
                a_uuid, b_uuid = b_uuid, a_uuid

            stmt = (
                pg_insert(CoBidding)
                .values(
                    contractor_a_id=a_uuid,
                    contractor_b_id=b_uuid,
                    co_bid_count=pair["co_bid_count"],
                    last_co_bid_date=datetime.now(timezone.utc).date(),
                )
                .on_conflict_do_update(
                    constraint="co_bidding_unique",
                    set_={"co_bid_count": pair["co_bid_count"], "updated_at": now},
                )
            )
            await self.db.execute(stmt)

        logger.info(f"Upserted {len(pairs)} co-bidding relationships")

    # ── step 8: contractor aggregate stats ─────────────────────────────────────

    async def _update_contractor_stats(self) -> None:
        if self.dry_run:
            return

        logger.info("Updating contractor aggregate stats...")
        await self.db.execute(text("""
            UPDATE contractors c
            SET
                total_tenders = sub.total_tenders,
                total_wins    = sub.total_wins,
                total_value_won = sub.total_value_won,
                win_rate = CASE WHEN sub.total_tenders > 0
                               THEN sub.total_wins::numeric / sub.total_tenders
                               ELSE 0 END,
                last_seen_at = NOW(),
                updated_at   = NOW()
            FROM (
                SELECT
                    b.contractor_id,
                    COUNT(DISTINCT b.tender_id)                        AS total_tenders,
                    COUNT(DISTINCT t.id) FILTER (WHERE t.winner_id = b.contractor_id)
                                                                       AS total_wins,
                    COALESCE(SUM(t.award_value) FILTER (WHERE t.winner_id = b.contractor_id), 0)
                                                                       AS total_value_won
                FROM bids b
                JOIN tenders t ON t.id = b.tender_id
                GROUP BY b.contractor_id
            ) sub
            WHERE c.id = sub.contractor_id
        """))

    # ── step 9: region stats ───────────────────────────────────────────────────

    async def _update_region_stats(self) -> None:
        if self.dry_run:
            return

        logger.info("Refreshing region stats...")
        await self.db.execute(text("""
            UPDATE region_stats rs
            SET
                total_tenders     = agg.total_tenders,
                total_value       = agg.total_value,
                high_risk_tenders = agg.high_risk_tenders,
                avg_risk_score    = agg.avg_risk_score,
                single_bidder_rate= agg.single_bidder_rate,
                calculated_at     = NOW()
            FROM (
                SELECT
                    region,
                    COUNT(*)                                            AS total_tenders,
                    COALESCE(SUM(expected_value), 0)                   AS total_value,
                    COUNT(*) FILTER (WHERE risk_score >= 50)           AS high_risk_tenders,
                    AVG(risk_score)                                     AS avg_risk_score,
                    AVG(CASE WHEN is_single_bidder THEN 1.0 ELSE 0.0 END)
                                                                       AS single_bidder_rate
                FROM tenders
                WHERE region IS NOT NULL
                GROUP BY region
            ) agg
            WHERE rs.region = agg.region
        """))

    # ── step 10: create alerts ─────────────────────────────────────────────────

    async def _create_alerts(self, df: pd.DataFrame) -> None:
        if self.dry_run:
            return

        high_risk = df[df["risk_score"] >= 50]
        logger.info(f"Creating alerts for {len(high_risk)} high-risk tenders...")

        now = datetime.now(timezone.utc)
        for _, row in high_risk.iterrows():
            tender_uuid = self.prozorro_to_tender_uuid.get(row["prozorro_id"])
            if not tender_uuid:
                continue

            winner_uuid = self.edrpou_to_uuid.get(str(row.get("winner_id", "")))
            risk_factors = row.get("risk_factors", {}) or {}
            reasons = risk_factors.get("reasons", [])

            stmt = (
                pg_insert(Alert)
                .values(
                    alert_type="tender",
                    tender_id=tender_uuid,
                    contractor_id=winner_uuid,
                    risk_score=float(row["risk_score"]),
                    risk_category=row["risk_category"],
                    reasons=reasons,
                    value_at_risk=row.get("expected_value"),
                    is_active=True,
                    detected_at=now,
                )
                .on_conflict_do_nothing()
            )
            await self.db.execute(stmt)
            self.stats["alerts_created"] += 1

    # ── sync log helpers ───────────────────────────────────────────────────────

    async def _start_sync_log(self) -> Optional[UUID]:
        if self.dry_run:
            return None
        entry = SyncLog(sync_type="incremental", status="running")
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry.id

    async def _finish_sync_log(
        self,
        log_id: Optional[UUID],
        success: bool,
        error: str = "",
    ) -> None:
        if self.dry_run or log_id is None:
            return
        await self.db.execute(
            update(SyncLog)
            .where(SyncLog.id == log_id)
            .values(
                completed_at=datetime.now(timezone.utc),
                status="completed" if success else "failed",
                records_fetched=self.stats["tenders_fetched"],
                records_created=self.stats["tenders_created"],
                records_updated=self.stats["tenders_updated"],
                errors=self.stats["errors"],
                error_message=error or None,
            )
        )
        await self.db.commit()

    def _print_summary(self) -> None:
        logger.info("=" * 50)
        logger.info("Sync complete:")
        for k, v in self.stats.items():
            logger.info(f"  {k}: {v}")
        logger.info("=" * 50)


# ── CLI entry point ────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Sync Prozorro data")
    parser.add_argument("--count", type=int, default=1000, help="Number of tenders to sync")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and score but don't save")
    args = parser.parse_args()

    logger.info(f"Starting Prozorro sync (count={args.count}, dry_run={args.dry_run})")

    async with AsyncSessionLocal() as db:
        syncer = ProzorroSyncer(db, dry_run=args.dry_run)
        await syncer.run(count=args.count)


if __name__ == "__main__":
    asyncio.run(main())
