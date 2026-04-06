"""
Enrichment Service

Orchestrates external data enrichment for contractors.
Phase 1: OpenSanctions (sanctions + PEP screening)
Phase 2: EDR (Ukrainian company registry — directors)
Phase 3: NAZK (asset declarations — conflict of interest)
Phase 4: GLEIF (international parent structures)
"""

from datetime import datetime, timezone
from uuid import UUID

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.contractor import Contractor
from app.models.contractor_director import ContractorDirector
from app.models.alert import Alert
from app.services.opensanctions_client import OpenSanctionsClient
from app.services.edr_client import EDRClient


class EnrichmentService:
    """Enriches contractor records with external intelligence sources."""

    def __init__(self):
        self.opensanctions = OpenSanctionsClient()
        self.edr = EDRClient()

    async def close(self):
        await self.opensanctions.close()
        await self.edr.close()

    # ── Public API ──────────────────────────────────────────────────────────────

    async def enrich_batch(
        self,
        contractors: list[Contractor],
        db: AsyncSession,
    ) -> dict:
        """
        Enrich a list of contractors with all available sources.
        Processes in batches to respect API limits.

        Returns stats dict: { enriched, sanctions_hits, pep_hits, errors }
        """
        stats = {
            "enriched": 0,
            "sanctions_hits": 0,
            "pep_hits": 0,
            "errors": 0,
            "directors_fetched": 0,
            "edr_dissolved": 0,
        }
        batch_size = settings.OPENSANCTIONS_BATCH_SIZE

        for i in range(0, len(contractors), batch_size):
            chunk = contractors[i : i + batch_size]
            try:
                chunk_stats = await self._enrich_chunk_opensanctions(chunk, db)
                stats["enriched"] += chunk_stats["enriched"]
                stats["sanctions_hits"] += chunk_stats["sanctions_hits"]
                stats["pep_hits"] += chunk_stats["pep_hits"]
            except Exception as e:
                logger.error(f"Enrichment chunk failed: {e}")
                stats["errors"] += len(chunk)

        if settings.EDR_ENABLED:
            for contractor in contractors:
                try:
                    edr_stats = await self._enrich_single_edr(contractor, db)
                    stats["directors_fetched"] += edr_stats["directors_fetched"]
                    stats["edr_dissolved"] += edr_stats["edr_dissolved"]
                except Exception as e:
                    logger.error(f"EDR enrichment failed for {contractor.edrpou}: {e}")

        return stats

    # ── OpenSanctions ────────────────────────────────────────────────────────────

    async def _enrich_chunk_opensanctions(
        self,
        contractors: list[Contractor],
        db: AsyncSession,
    ) -> dict:
        stats = {"enriched": 0, "sanctions_hits": 0, "pep_hits": 0}

        entities = [
            {"id": str(c.id), "name": c.name, "edrpou": c.edrpou}
            for c in contractors
        ]

        results = await self.opensanctions.match_batch(entities)
        now = datetime.now(timezone.utc)

        for contractor in contractors:
            result = results.get(str(contractor.id))
            if result is None:
                continue

            is_sanctioned = result["matched"] and not all(
                h["is_pep"] for h in result["hits"]
            )
            is_pep = result["matched"] and any(h["is_pep"] for h in result["hits"])
            # If all hits are PEP-only, is_sanctioned stays False
            if result["matched"] and all(h["is_pep"] for h in result["hits"]):
                is_sanctioned = False

            update_values = dict(
                is_sanctioned=is_sanctioned,
                is_pep=is_pep,
                sanctions_hits=result["hits"],
                enriched_at=now,
            )
            # Sanctioned contractors are forced to critical risk
            if is_sanctioned:
                update_values["risk_score"] = 100.0
                update_values["risk_category"] = "critical"

            await db.execute(
                update(Contractor)
                .where(Contractor.id == contractor.id)
                .values(**update_values)
            )

            stats["enriched"] += 1
            if is_sanctioned:
                stats["sanctions_hits"] += 1
                await self._create_sanctions_alert(contractor, result["hits"], db)
            if is_pep:
                stats["pep_hits"] += 1

        logger.info(
            f"OpenSanctions chunk: {stats['enriched']} enriched, "
            f"{stats['sanctions_hits']} sanctions hits, "
            f"{stats['pep_hits']} PEP hits"
        )
        return stats

    async def _create_sanctions_alert(
        self,
        contractor: Contractor,
        hits: list[dict],
        db: AsyncSession,
    ) -> None:
        """Create a SANCTIONED_ENTITY_CONTRACT alert for a contractor."""
        # Build human-readable reasons
        reasons = []
        for hit in hits:
            datasets_str = ", ".join(hit.get("datasets", []))
            reasons.append(
                f"Matched '{hit.get('name')}' on sanctions list(s): {datasets_str} "
                f"(score: {hit.get('score', 0):.0%})"
            )

        stmt = (
            pg_insert(Alert)
            .values(
                alert_type="sanctioned_entity",
                contractor_id=contractor.id,
                tender_id=None,
                risk_score=100.0,
                risk_category="critical",
                reasons=reasons,
                value_at_risk=contractor.total_value_won,
                is_active=True,
                detected_at=datetime.now(timezone.utc),
            )
            # Only one active sanctions alert per contractor
            .on_conflict_do_nothing()
        )
        await db.execute(stmt)
        logger.warning(
            f"SANCTIONS ALERT: {contractor.name} (EDRPOU {contractor.edrpou}) "
            f"matched {len(hits)} sanctions/PEP record(s)"
        )

    # ── EDR ──────────────────────────────────────────────────────────────────────

    async def _enrich_single_edr(
        self,
        contractor: Contractor,
        db: AsyncSession,
    ) -> dict:
        stats = {"directors_fetched": 0, "edr_dissolved": 0}
        now = datetime.now(timezone.utc)

        result = await self.edr.get_company(contractor.edrpou)

        if result is None:
            await db.execute(
                update(Contractor)
                .where(Contractor.id == contractor.id)
                .values(edr_status="unknown", directors_fetched_at=now)
            )
            return stats

        edr_status = result.get("status", "unknown")

        for person in result.get("directors", []):
            stmt = (
                pg_insert(ContractorDirector)
                .values(
                    contractor_id=contractor.id,
                    full_name=person["full_name"],
                    role=person.get("role"),
                    source="edr",
                    fetched_at=now,
                )
                .on_conflict_do_update(
                    index_elements=["contractor_id", "full_name"],
                    set_={"role": person.get("role"), "fetched_at": now},
                )
            )
            await db.execute(stmt)
            stats["directors_fetched"] += 1

        await db.execute(
            update(Contractor)
            .where(Contractor.id == contractor.id)
            .values(edr_status=edr_status, directors_fetched_at=now)
        )

        if edr_status == "dissolved":
            stats["edr_dissolved"] += 1
            logger.warning(
                f"EDR DISSOLVED: {contractor.name} (EDRPOU {contractor.edrpou})"
            )

        return stats
