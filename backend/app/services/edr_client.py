"""
EDR Client

Fetches company officer / founder data from Ukraine's EDR (Єдиний державний
реєстр юридичних осіб) via the OpenProcurement sandbox endpoint.

The sandbox DNS is unreachable in 2026, so this client is guarded by
EDR_ENABLED=False.  Flip to True once a working endpoint is confirmed.
"""

import asyncio
from typing import Optional

import httpx
from loguru import logger

from app.config import settings

# Ukrainian document keywords that appear as "founders" but are just references
_DOCUMENT_KEYWORDS = (
    "УКАЗ", "ПОСТАНОВА", "ЗАКОН", "НАКАЗ", "РІШЕННЯ",
    "РОЗПОРЯДЖЕННЯ", "ДЕКРЕТ", "СТАТУТ",
)

_STATUS_MAP = {
    "registered": "active",
    "cancelled": "dissolved",
    "terminated": "dissolved",
    "bankrupt": "dissolved",
}

_ROLE_MAP = {
    "керівник": "director",
    "директор": "director",
    "генеральний директор": "director",
    "президент": "director",
    "виконавчий директор": "director",
    "засновник": "founder",
    "учасник": "founder",
    "підписант": "signatory",
    "бенефіціарний власник": "beneficial_owner",
    "кінцевий бенефіціарний власник": "beneficial_owner",
}


class EDRClient:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=settings.EDR_TIMEOUT,
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── Public API ───────────────────────────────────────────────────────────

    async def get_company(self, edrpou: str) -> Optional[dict]:
        """
        Returns {name, status, directors: [{full_name, role}]} or None on error.
        """
        try:
            verify_data = await self._verify(edrpou)
            if not verify_data:
                return None

            subject_url = verify_data.get("url") or verify_data.get("identification", {}).get("url")
            registration_status = verify_data.get("registrationStatus", "")

            directors = []
            if subject_url:
                directors = await self._fetch_directors(subject_url)

            return {
                "name": verify_data.get("name", ""),
                "status": self._parse_status(registration_status),
                "directors": directors,
            }
        except Exception as exc:
            logger.error(f"EDR get_company({edrpou}) unexpected error: {exc}")
            return None

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _verify(self, edrpou: str) -> Optional[dict]:
        url = f"{settings.EDR_API_URL}?id={edrpou}"
        data = await self._get_with_retry(url)
        if data is None:
            return None

        # Response may be a list or a dict with a "data" key
        if isinstance(data, list):
            return data[0] if data else None
        if isinstance(data, dict):
            inner = data.get("data")
            if isinstance(inner, list):
                return inner[0] if inner else None
            return data
        return None

    async def _fetch_directors(self, subject_url: str) -> list[dict]:
        data = await self._get_with_retry(subject_url)
        if not data:
            return []

        if isinstance(data, dict) and "data" in data:
            data = data["data"]

        people = []

        heads = data.get("heads", []) if isinstance(data, dict) else []
        for head in heads:
            name = (head.get("name") or "").strip()
            if not name or self._is_document_reference(name):
                continue
            role_text = (head.get("role") or "").lower()
            people.append({
                "full_name": name,
                "role": self._normalize_role(role_text, is_head=True),
            })

        founders = data.get("founders", []) if isinstance(data, dict) else []
        for founder in founders:
            name = (founder.get("name") or "").strip()
            if not name or self._is_document_reference(name):
                continue
            role_text = (founder.get("role") or "").lower()
            people.append({
                "full_name": name,
                "role": self._normalize_role(role_text, is_head=False),
            })

        return people

    async def _get_with_retry(self, url: str, retries: int = 2) -> Optional[dict]:
        for attempt in range(retries + 1):
            try:
                resp = await self.client.get(url)
                if resp.status_code == 404:
                    return None
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", "10"))
                    logger.warning(f"EDR rate limit hit; waiting {wait}s")
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException:
                logger.warning(f"EDR timeout on {url} (attempt {attempt + 1})")
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)
            except httpx.NetworkError as exc:
                logger.warning(f"EDR network error on {url}: {exc}")
                return None
            except Exception as exc:
                logger.error(f"EDR request error on {url}: {exc}")
                return None
        return None

    @staticmethod
    def _parse_status(registration_status: str) -> str:
        key = (registration_status or "").lower()
        for k, v in _STATUS_MAP.items():
            if k in key:
                return v
        return "unknown"

    @staticmethod
    def _normalize_role(role_text: str, is_head: bool) -> str:
        role_text = role_text.lower().strip()
        for ukr, eng in _ROLE_MAP.items():
            if ukr in role_text:
                return eng
        return "director" if is_head else "founder"

    @staticmethod
    def _is_document_reference(name: str) -> bool:
        upper = name.upper()
        return any(kw in upper for kw in _DOCUMENT_KEYWORDS)
