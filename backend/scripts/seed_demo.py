#!/usr/bin/env python3
"""
seed_demo.py

Generates realistic synthetic procurement data for demo/development.
Does NOT call the Prozorro API — useful for local dev with no internet.

Seeds:
  - 25 government buyers (one per region)
  - 80 contractors
  - 500 tenders with varied risk patterns
  - Bids, co-bidding relationships, alerts, region stats

Usage:
    python scripts/seed_demo.py
    python scripts/seed_demo.py --tenders 200   # smaller seed
    python scripts/seed_demo.py --reset         # drop all data first
"""

import asyncio
import argparse
import random
import sys
import os
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.models.contractor import Contractor
from app.models.buyer import Buyer
from app.models.tender import Tender
from app.models.bid import Bid
from app.models.co_bidding import CoBidding
from app.models.alert import Alert
from app.models.region_stats import RegionStats
from app.models.sync_log import SyncLog
from app.services.risk_engine import RiskScoringEngine

import pandas as pd
import numpy as np

# ── Static reference data ───────────────────────────────────────────────────────

REGIONS = [
    "Київська область", "Харківська область", "Одеська область",
    "Дніпропетровська область", "Львівська область", "Запорізька область",
    "Миколаївська область", "Херсонська область", "Донецька область",
    "Чернігівська область", "Сумська область", "Полтавська область",
    "Вінницька область", "Житомирська область", "Волинська область",
    "Рівненська область", "Івано-Франківська область", "Тернопільська область",
    "Хмельницька область", "Черкаська область", "Кіровоградська область",
    "Чернівецька область", "Закарпатська область", "Луганська область",
    "м. Київ",
]

CPV_CATEGORIES = [
    ("45000000", "Будівельні роботи"),
    ("33000000", "Медичне обладнання"),
    ("48000000", "Програмне забезпечення"),
    ("72000000", "ІТ-послуги"),
    ("60000000", "Транспортні послуги"),
    ("45200000", "Дорожні роботи"),
    ("39000000", "Меблі та обладнання"),
    ("31000000", "Електрообладнання"),
    ("34000000", "Транспортні засоби"),
    ("55000000", "Готельні та ресторанні послуги"),
]

BUYER_NAMES = [
    "Міністерство охорони здоров'я України",
    "Міністерство освіти і науки України",
    "Міністерство інфраструктури України",
    "Міністерство оборони України",
    "Міністерство фінансів України",
    "Київська міська рада",
    "Харківська обласна державна адміністрація",
    "Одеська міська рада",
    "Дніпропетровська ОДА",
    "Державне агентство автомобільних доріг України",
    "Укрзалізниця",
    "Національна служба здоров'я України",
    "Державна служба надзвичайних ситуацій",
    "Міністерство аграрної політики",
    "Державне підприємство «Документ»",
]

CONTRACTOR_PREFIXES = [
    "ТОВ", "ПрАТ", "ДП", "ПП", "ФОП",
]

CONTRACTOR_NAMES = [
    "БУД-СЕРВІС", "ТЕХНО-ГРУП", "УКРБУДІНВЕСТ", "МЕГАПРОЕКТ", "АЛЬФА-БУД",
    "БУДІВЕЛЬНА КОМПАНІЯ «СОЛІД»", "МЕДТЕХ УКРАЇНА", "ФАРМАЦЕВТИЧНА КОМПАНІЯ",
    "ІТ-РІШЕННЯ ПЛЮС", "DIGITAL SOLUTIONS UA", "ТРАНС-ЛОГІСТИК", "АВТО-СЕРВІС",
    "ДОРОЖНІЙ СТАНДАРТ", "ЕЛЕКТРОМОНТАЖ-ЗАХІД", "МЕБЛЕВИЙ ЦЕНТР",
    "БУДПОСТАЧ", "КОНСТРУКТИВ-ПЛЮС", "РЕМОНТ І БУДІВНИЦТВО", "ЯКІСТЬ-БУД",
    "ЗАХІД-ТРАНС", "СХІД-БУДДЕТАЛЬ", "ЦЕНТР-ІНВЕСТ", "ГАРАНТІЯ-БУД",
    "НОВА ТЕХНОЛОГІЯ", "ПРОЕКТ-ЦЕНТР", "СЕРВІСНА МЕРЕЖА", "УКРІНФРА",
    "БУДГРУПП ХОЛДІНГ", "ТЕХРЕЗЕРВ", "СТАНДАРТ-БУД",
    "ІНФОБУД", "КІБЕРСИСТЕМ", "ЗАХИСНИЙ КОМПЛЕКС", "ПРЕМ'ЄР-БУД",
    "СУЧАСНІ ТЕХНОЛОГІЇ", "ПРОФІТ-ГРУП", "КОНСОРЦІУМ «ПРОГРЕС»",
    "УКРЕНЕРГОМОНТАЖ", "МЕТАЛОПРОКАТ", "ФІНАНСОВИЙ КОНСАЛТИНГ",
    "ПРОМБУДСЕРВІС", "РЕГІОН-ПОСТАЧ", "ГАЛАКТИКА-ТРЕЙД", "КОНТИНЕНТ-БУД",
    "ВЕКТОР-ТЕХНОЛОГІЙ", "СИСТЕМНА ІНТЕГРАЦІЯ", "АЛЬЯНС-ПОСТАЧ",
    "ДНІПРОБУД", "КАРПАТБУД", "ПРИЧОРНОМОРСЬКБУД",
    "БУДІВЕЛЬНИЙ АЛЬЯНС", "ІННОВАЦІЙНІ СИСТЕМИ", "ЗЕЛЕНИЙ СТАНДАРТ",
    "АКТИВ-ТРЕЙД", "ЛОГІСТИЧНИЙ ЦЕНТР", "МАКСИМУМ-ПОСТАЧ",
    "БІЗНЕС-РІШЕННЯ", "ПРОФІЛЬ-ЗАХІД", "ЄВРОБУДСТАНДАРТ",
    "УКРСПЕЦМОНТАЖ", "ПРОГРЕС-КОМПЛЕКС", "СТРОЙНОРМ",
    "АГРОБУДТЕХ", "ТЕХНОПАРК", "СИСТЕМНІ РІШЕННЯ", "РЕГІОНАЛЬНИЙ ПОСТАЧ",
    "ФОРС-ГРУП", "ПРІМА-БУД", "МАСТЕРБУД", "ОПТИМУМ-ТРЕЙД",
    "МОДЕРНІЗАЦІЯ", "КОМПЛЕКС-БУД", "ІНДУСТРІЯ ПЛЮС", "НОВИЙ СТАНДАРТ",
    "ЗАХІД-ІНВЕСТ", "СХІД-КОНСОРЦІУМ", "ЦЕНТРБУДСЕРВІС", "ПРОФІМАРКЕТ",
    "ГАРАНТБУД", "ГЛОБАЛЬНИЙ ПОСТАЧ",
]


def rand_edrpou() -> str:
    return str(random.randint(10_000_000, 99_999_999))


def rand_date(days_back: int = 365) -> datetime:
    delta = random.randint(0, days_back)
    return datetime.now(timezone.utc) - timedelta(days=delta)


def rand_value(min_v=50_000, max_v=50_000_000) -> float:
    # Log-normal distribution to match real procurement values
    return round(np.random.lognormal(mean=13, sigma=2), 2)


# ── seeder ─────────────────────────────────────────────────────────────────────

class DemoSeeder:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.buyer_ids: list[object] = []
        self.contractor_ids: list[object] = []
        self.tender_ids: list[object] = []

    async def run(self, num_tenders: int = 500, reset: bool = False) -> None:
        if reset:
            await self._reset()

        logger.info("Seeding demo data...")
        await self._seed_buyers()
        await self._seed_contractors()
        await self._seed_tenders(num_tenders)
        await self._seed_co_bidding()
        await self._update_region_stats()
        await self._seed_sync_log()
        await self.db.commit()
        logger.info(f"Done. Seeded {len(self.buyer_ids)} buyers, "
                    f"{len(self.contractor_ids)} contractors, "
                    f"{len(self.tender_ids)} tenders.")

    # ── reset ────────────────────────────────────────────────────────────────────

    async def _reset(self) -> None:
        logger.warning("Resetting all data...")
        for tbl in ("alerts", "co_bidding", "bids", "tenders", "buyers",
                    "contractors", "sync_log"):
            await self.db.execute(text(f"TRUNCATE {tbl} CASCADE"))
        await self.db.commit()
        logger.info("Reset complete")

    # ── buyers ───────────────────────────────────────────────────────────────────

    async def _seed_buyers(self) -> None:
        names = BUYER_NAMES + [f"Управління охорони здоров'я {r}" for r in REGIONS[:10]]
        used = set()
        for i, name in enumerate(names[:25]):
            region = REGIONS[i % len(REGIONS)]
            prozorro_id = f"UA-EDR-{rand_edrpou()}"
            while prozorro_id in used:
                prozorro_id = f"UA-EDR-{rand_edrpou()}"
            used.add(prozorro_id)

            stmt = (
                pg_insert(Buyer)
                .values(
                    prozorro_id=prozorro_id,
                    edrpou=rand_edrpou(),
                    name=name,
                    name_normalized=name.lower(),
                    region=region,
                    buyer_type=random.choice(["central", "regional", "local"]),
                    total_tenders=0,
                    total_value=0,
                )
                .on_conflict_do_update(
                    index_elements=["prozorro_id"],
                    set_={"name": name},
                )
                .returning(Buyer.id)
            )
            result = await self.db.execute(stmt)
            row = result.fetchone()
            if row:
                self.buyer_ids.append(row[0])

        await self.db.commit()
        logger.info(f"Seeded {len(self.buyer_ids)} buyers")

    # ── contractors ──────────────────────────────────────────────────────────────

    async def _seed_contractors(self) -> None:
        used_edrpou = set()
        names = CONTRACTOR_NAMES[:]
        random.shuffle(names)

        for name in names[:80]:
            edrpou = rand_edrpou()
            while edrpou in used_edrpou:
                edrpou = rand_edrpou()
            used_edrpou.add(edrpou)

            full_name = f"{random.choice(CONTRACTOR_PREFIXES)} «{name}»"
            region = random.choice(REGIONS)

            stmt = (
                pg_insert(Contractor)
                .values(
                    edrpou=edrpou,
                    name=full_name,
                    name_normalized=full_name.lower(),
                    region=region,
                    is_active=True,
                    first_seen_at=rand_date(730),
                    last_seen_at=rand_date(30),
                )
                .on_conflict_do_update(
                    index_elements=["edrpou"],
                    set_={"name": full_name},
                )
                .returning(Contractor.id)
            )
            result = await self.db.execute(stmt)
            row = result.fetchone()
            if row:
                self.contractor_ids.append(row[0])

        await self.db.commit()
        logger.info(f"Seeded {len(self.contractor_ids)} contractors")

    # ── tenders + bids + risk scoring ────────────────────────────────────────────

    async def _seed_tenders(self, num_tenders: int) -> None:
        logger.info(f"Seeding {num_tenders} tenders with risk scoring...")

        # Build raw data records for risk engine
        records = []
        for i in range(num_tenders):
            cpv_code, cpv_desc = random.choice(CPV_CATEGORIES)
            buyer_id = random.choice(self.buyer_ids)
            region = random.choice(REGIONS)
            expected_value = rand_value()
            date_mod = rand_date(180)

            # Bid pattern: mostly competitive, some rigged
            pattern = random.choices(
                ["competitive", "single", "suspicious_spread", "high_value_rigged"],
                weights=[60, 20, 10, 10],
            )[0]

            if pattern == "single":
                num_bids = 1
                winner_idx = 0
                bidder_indices = [random.randint(0, len(self.contractor_ids) - 1)]
                bid_amounts = [expected_value * random.uniform(0.95, 1.05)]
            elif pattern == "suspicious_spread":
                num_bids = random.randint(2, 4)
                bidder_indices = random.sample(range(len(self.contractor_ids)), num_bids)
                winner_idx = 0
                base = expected_value
                # Very tight spread — suspicious
                bid_amounts = [base * random.uniform(0.999, 1.001) for _ in range(num_bids)]
            elif pattern == "high_value_rigged":
                num_bids = random.randint(2, 3)
                bidder_indices = random.sample(range(len(self.contractor_ids)), num_bids)
                winner_idx = 0
                bid_amounts = [expected_value * 1.5] + [
                    expected_value * random.uniform(1.51, 1.6)
                    for _ in range(num_bids - 1)
                ]
                expected_value *= 1.5  # inflated
            else:
                num_bids = random.randint(2, 8)
                bidder_indices = random.sample(
                    range(len(self.contractor_ids)), min(num_bids, len(self.contractor_ids))
                )
                winner_idx = 0
                spread = random.uniform(0.05, 0.30)
                bid_amounts = sorted([
                    expected_value * random.uniform(0.85, 1.15)
                    for _ in range(len(bidder_indices))
                ])

            winner_idx_actual = bidder_indices[0] if bidder_indices else 0
            winner_id = self.contractor_ids[winner_idx_actual]
            bidder_ids = [self.contractor_ids[idx] for idx in bidder_indices]
            bidder_edrpous = []  # not needed for scoring

            records.append({
                "prozorro_id": f"UA-{date_mod.strftime('%Y-%m-%d')}-{i:06d}",
                "title": f"Закупівля: {cpv_desc} #{i:04d}",
                "cpv_code": cpv_code,
                "cpv_description": cpv_desc,
                "expected_value": float(expected_value),
                "num_bids": len(bidder_indices),
                "bid_amounts": bid_amounts,
                "bidder_ids": bidder_edrpous,
                "is_single_bidder": len(bidder_indices) <= 1,
                # internal tracking
                "_buyer_id": buyer_id,
                "_winner_id": winner_id,
                "_bidder_ids": bidder_ids,
                "_bid_amounts": bid_amounts,
                "_region": region,
                "_date_mod": date_mod,
            })

        # Run risk scoring in one batch
        df = pd.DataFrame(records)
        engine = RiskScoringEngine()
        scored_df = engine.score_tenders(df)

        # Persist to DB
        for _, row in scored_df.iterrows():
            date_mod = row["_date_mod"]
            tender_stmt = (
                pg_insert(Tender)
                .values(
                    prozorro_id=row["prozorro_id"],
                    title=row["title"],
                    status=random.choice(["complete", "complete", "complete", "active"]),
                    procurement_method="open",
                    procurement_method_type="aboveThresholdUA",
                    expected_value=row["expected_value"],
                    currency="UAH",
                    cpv_code=row["cpv_code"],
                    cpv_description=row["cpv_description"],
                    buyer_id=row["_buyer_id"],
                    winner_id=row["_winner_id"],
                    award_value=row["bid_amounts"][0] if row["bid_amounts"] else row["expected_value"],
                    award_date=date_mod.date(),
                    num_bids=row["num_bids"],
                    date_modified=date_mod,
                    region=row["_region"],
                    risk_score=float(row["risk_score"]),
                    risk_category=row["risk_category"],
                    risk_factors=row["risk_factors"],
                    is_single_bidder=bool(row.get("is_single_bidder", False)),
                    is_price_anomaly=bool(row.get("is_price_anomaly", False)),
                    is_bid_pattern_anomaly=bool(row.get("is_bid_pattern_anomaly", False)),
                    risk_updated_at=datetime.now(timezone.utc),
                )
                .on_conflict_do_update(
                    index_elements=["prozorro_id"],
                    set_={"risk_score": float(row["risk_score"])},
                )
                .returning(Tender.id)
            )
            t_result = await self.db.execute(tender_stmt)
            t_row = t_result.fetchone()
            if not t_row:
                continue
            tender_uuid = t_row[0]
            self.tender_ids.append(tender_uuid)

            # Bids
            for bidder_uuid, bid_val in zip(row["_bidder_ids"], row["_bid_amounts"]):
                is_win = bidder_uuid == row["_winner_id"]
                await self.db.execute(
                    pg_insert(Bid)
                    .values(
                        tender_id=tender_uuid,
                        contractor_id=bidder_uuid,
                        bid_value=float(bid_val),
                        currency="UAH",
                        status="active",
                        is_winner=is_win,
                        bid_date=date_mod,
                    )
                    .on_conflict_do_nothing()
                )

            # Alert for high-risk tenders
            if row["risk_score"] >= 50:
                reasons = (row["risk_factors"] or {}).get("reasons", [])
                await self.db.execute(
                    pg_insert(Alert)
                    .values(
                        alert_type="tender",
                        tender_id=tender_uuid,
                        contractor_id=row["_winner_id"],
                        risk_score=float(row["risk_score"]),
                        risk_category=row["risk_category"],
                        reasons=reasons,
                        value_at_risk=row["expected_value"],
                        is_active=True,
                        detected_at=date_mod,
                    )
                    .on_conflict_do_nothing()
                )

        await self.db.commit()

        # Update contractor aggregate stats
        await self.db.execute(text("""
            UPDATE contractors c
            SET
                total_tenders   = sub.total_tenders,
                total_wins      = sub.total_wins,
                total_value_won = sub.total_value_won,
                win_rate = CASE WHEN sub.total_tenders > 0
                               THEN sub.total_wins::numeric / sub.total_tenders
                               ELSE 0 END,
                risk_score      = sub.avg_risk,
                risk_category   = CASE
                    WHEN sub.avg_risk >= 75 THEN 'critical'
                    WHEN sub.avg_risk >= 50 THEN 'high'
                    WHEN sub.avg_risk >= 25 THEN 'medium'
                    ELSE 'low' END,
                risk_updated_at = NOW(),
                updated_at      = NOW()
            FROM (
                SELECT
                    b.contractor_id,
                    COUNT(DISTINCT b.tender_id)                          AS total_tenders,
                    COUNT(DISTINCT t.id) FILTER (WHERE t.winner_id = b.contractor_id)
                                                                         AS total_wins,
                    COALESCE(SUM(t.award_value) FILTER (WHERE t.winner_id = b.contractor_id), 0)
                                                                         AS total_value_won,
                    COALESCE(AVG(t.risk_score) FILTER (WHERE t.winner_id = b.contractor_id), 0)
                                                                         AS avg_risk
                FROM bids b
                JOIN tenders t ON t.id = b.tender_id
                GROUP BY b.contractor_id
            ) sub
            WHERE c.id = sub.contractor_id
        """))
        await self.db.commit()
        logger.info(f"Seeded {len(self.tender_ids)} tenders")

    # ── co-bidding ────────────────────────────────────────────────────────────────

    async def _seed_co_bidding(self) -> None:
        """Build co-bidding pairs from actual bids in DB."""
        logger.info("Building co-bidding relationships...")
        await self.db.execute(text("""
            INSERT INTO co_bidding (contractor_a_id, contractor_b_id, co_bid_count,
                                    first_co_bid_date, last_co_bid_date)
            SELECT
                LEAST(b1.contractor_id, b2.contractor_id)    AS contractor_a_id,
                GREATEST(b1.contractor_id, b2.contractor_id) AS contractor_b_id,
                COUNT(*)                                      AS co_bid_count,
                MIN(t.award_date)                             AS first_co_bid_date,
                MAX(t.award_date)                             AS last_co_bid_date
            FROM bids b1
            JOIN bids b2
                ON b1.tender_id = b2.tender_id
               AND b1.contractor_id < b2.contractor_id
            JOIN tenders t ON t.id = b1.tender_id
            GROUP BY 1, 2
            HAVING COUNT(*) >= 2
            ON CONFLICT ON CONSTRAINT co_bidding_unique
            DO UPDATE SET co_bid_count = EXCLUDED.co_bid_count
        """))
        await self.db.commit()

    # ── region stats ─────────────────────────────────────────────────────────────

    async def _update_region_stats(self) -> None:
        await self.db.execute(text("""
            UPDATE region_stats rs
            SET
                total_tenders      = agg.total_tenders,
                total_value        = agg.total_value,
                high_risk_tenders  = agg.high_risk_tenders,
                avg_risk_score     = agg.avg_risk_score,
                single_bidder_rate = agg.single_bidder_rate,
                calculated_at      = NOW()
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

    # ── sync log ─────────────────────────────────────────────────────────────────

    async def _seed_sync_log(self) -> None:
        now = datetime.now(timezone.utc)
        entry = SyncLog(
            sync_type="seed",
            started_at=now,
            completed_at=now,
            records_fetched=len(self.tender_ids),
            records_created=len(self.tender_ids),
            records_updated=0,
            errors=0,
            status="completed",
        )
        self.db.add(entry)


# ── CLI ────────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument("--tenders", type=int, default=500)
    parser.add_argument("--reset", action="store_true", help="Truncate all tables first")
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        seeder = DemoSeeder(db)
        await seeder.run(num_tenders=args.tenders, reset=args.reset)


if __name__ == "__main__":
    asyncio.run(main())
