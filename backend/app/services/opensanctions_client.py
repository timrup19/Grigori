"""
OpenSanctions API Client

Matches entities against the consolidated sanctions + PEP database.
API docs: https://www.opensanctions.org/docs/api/

Free for non-commercial use. Set OPENSANCTIONS_API_KEY in .env for commercial use.
"""

import asyncio
from typing import Optional
import httpx
from loguru import logger

from app.config import settings


class OpenSanctionsClient:
    """Client for the OpenSanctions match API."""

    BASE_URL = settings.OPENSANCTIONS_API_URL
    DATASET = "default"  # covers sanctions + PEPs across all sources

    def __init__(self):
        headers = {"Accept": "application/json"}
        if settings.OPENSANCTIONS_API_KEY:
            headers["Authorization"] = f"ApiKey {settings.OPENSANCTIONS_API_KEY}"

        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=headers,
            timeout=30,
        )

    async def close(self):
        await self.client.aclose()

    async def match_batch(self, entities: list[dict]) -> dict:
        """
        Match a batch of entities against the sanctions + PEP database.

        Args:
            entities: List of dicts with keys: id (str), name (str), edrpou (str)
                      id must be unique within the batch (used as query key).

        Returns:
            Dict mapping entity id → { matched: bool, score: float, hits: list }
        """
        if not entities:
            return {}

        queries = {}
        for e in entities:
            queries[e["id"]] = {
                "schema": "Company",
                "properties": {
                    "name": [e["name"]],
                    "jurisdiction": ["ua"],
                    # EDRPOU as registration number for stronger matching
                    "registrationNumber": [e["edrpou"]],
                },
            }

        try:
            response = await self.client.post(
                f"/match/{self.DATASET}",
                json={"queries": queries},
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"OpenSanctions rate limit hit, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                response = await self.client.post(
                    f"/match/{self.DATASET}",
                    json={"queries": queries},
                )

            response.raise_for_status()
            raw = response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenSanctions HTTP error: {e.response.status_code} — {e.response.text[:200]}")
            return {}
        except Exception as e:
            logger.error(f"OpenSanctions request failed: {e}")
            return {}

        results = {}
        responses = raw.get("responses", {})

        for entity_id, resp in responses.items():
            hits = []
            matched = False
            best_score = 0.0

            for result in resp.get("results", []):
                score = result.get("score", 0.0)
                if score < settings.OPENSANCTIONS_MIN_SCORE:
                    continue

                matched = True
                best_score = max(best_score, score)

                # Determine which datasets this entity appears in
                datasets = result.get("datasets", [])
                is_pep = any(
                    d in datasets
                    for d in ("peps", "ua_nazk_peps", "everypolitician", "wd_peps")
                )

                hits.append({
                    "id": result.get("id"),
                    "name": result.get("caption"),
                    "score": round(score, 3),
                    "is_pep": is_pep,
                    "datasets": datasets,
                    "properties": {
                        k: v for k, v in result.get("properties", {}).items()
                        if k in ("name", "country", "notes", "reason", "listingDate", "program")
                    },
                })

            results[entity_id] = {
                "matched": matched,
                "score": best_score,
                "hits": hits,
            }

        return results
