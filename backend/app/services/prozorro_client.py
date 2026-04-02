"""
Prozorro API Client

Fetches procurement data from Ukraine's public Prozorro API.
API Documentation: https://public-api.prozorro.gov.ua/api/2.5/
"""

import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger

from app.config import settings


class ProzorroClient:
    """
    Client for interacting with Prozorro's public API.
    """
    
    def __init__(self):
        self.base_url = settings.PROZORRO_API_BASE_URL
        self.timeout = settings.PROZORRO_API_TIMEOUT
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                'User-Agent': 'ProzorroSentinel/1.0 (Research Platform)',
                'Accept': 'application/json',
            }
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    # ========================================================================
    # Tenders
    # ========================================================================
    
    async def get_tenders(
        self,
        limit: int = 100,
        offset: Optional[str] = None,
        descending: bool = True
    ) -> Optional[Dict]:
        """
        Get list of tenders.
        
        Args:
            limit: Number of tenders to fetch (max 1000)
            offset: Pagination offset
            descending: Sort by date descending
        
        Returns:
            API response with 'data' and 'next_page' fields
        """
        params = {'limit': min(limit, 1000)}
        if offset:
            params['offset'] = offset
        if descending:
            params['descending'] = '1'
        
        try:
            response = await self.client.get(
                f"{self.base_url}/tenders",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching tenders: {e}")
            return None
    
    async def get_tender_details(self, tender_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific tender.
        
        Args:
            tender_id: Prozorro tender ID
        
        Returns:
            Full tender data including bids, awards, etc.
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/tenders/{tender_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Tender not found: {tender_id}")
            else:
                logger.error(f"Error fetching tender {tender_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching tender {tender_id}: {e}")
            return None
    
    async def search_tenders(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        region: Optional[str] = None,
        cpv: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100
    ) -> Optional[Dict]:
        """
        Search tenders with filters.
        
        Note: Prozorro API has limited search capabilities.
        For complex queries, fetch all and filter locally.
        """
        params = {'limit': min(limit, 1000)}
        
        # Build query parameters based on what Prozorro API supports
        # Note: Check actual API docs for supported filters
        
        try:
            response = await self.client.get(
                f"{self.base_url}/tenders",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error searching tenders: {e}")
            return None
    
    # ========================================================================
    # Fetch Multiple Tenders with Details
    # ========================================================================
    
    async def fetch_tenders_batch(
        self,
        num_tenders: int = 100,
        start_offset: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch multiple tenders with their full details.
        
        Args:
            num_tenders: Total number of tenders to fetch
            start_offset: Starting offset for pagination
        
        Returns:
            List of tender dictionaries with full details
        """
        logger.info(f"Fetching {num_tenders} tenders from Prozorro API...")
        
        # Get list of tender IDs
        tenders_list = await self.get_tenders(
            limit=min(num_tenders * 2, 1000),  # Fetch extra in case some fail
            offset=start_offset
        )
        
        if not tenders_list or 'data' not in tenders_list:
            logger.error("Failed to fetch tender list")
            return []
        
        detailed_tenders = []
        failed = 0
        
        for i, tender_summary in enumerate(tenders_list['data']):
            if len(detailed_tenders) >= num_tenders:
                break
            
            tender_id = tender_summary.get('id')
            if tender_id:
                details = await self.get_tender_details(tender_id)
                if details and 'data' in details:
                    detailed_tenders.append(details['data'])
                else:
                    failed += 1
            
            # Progress logging
            if (i + 1) % 50 == 0:
                logger.info(f"Progress: {len(detailed_tenders)}/{num_tenders} fetched...")
        
        logger.info(f"Fetched {len(detailed_tenders)} tenders ({failed} failed)")
        
        return detailed_tenders
    
    # ========================================================================
    # Data Parsing
    # ========================================================================
    
    def parse_tender(self, tender: Dict) -> Dict:
        """
        Parse raw Prozorro tender data into our schema format.
        
        Args:
            tender: Raw tender data from API
        
        Returns:
            Parsed tender dictionary matching our schema
        """
        try:
            # Basic info
            tender_id = tender.get('id', '')
            status = tender.get('status', '')
            procurement_method = tender.get('procurementMethod', '')
            procurement_method_type = tender.get('procurementMethodType', '')
            
            # Value
            value = tender.get('value', {})
            expected_value = value.get('amount', 0)
            currency = value.get('currency', 'UAH')
            
            # Procuring entity (buyer)
            procuring_entity = tender.get('procuringEntity', {})
            buyer_name = procuring_entity.get('name', '')
            buyer_id = procuring_entity.get('identifier', {}).get('id', '')
            buyer_region = procuring_entity.get('address', {}).get('region', '')
            
            # Classification (CPV)
            classification = tender.get('classification', {})
            cpv_code = classification.get('id', '')[:8] if classification.get('id') else ''
            cpv_description = classification.get('description', '')
            
            # Dates
            date_modified = tender.get('dateModified', '')
            tender_period = tender.get('tenderPeriod', {})
            start_date = tender_period.get('startDate', '')
            end_date = tender_period.get('endDate', '')
            
            # Bids
            bids = tender.get('bids', [])
            num_bids = len(bids)
            
            bid_amounts = []
            bidder_ids = []
            bidder_names = []
            
            for bid in bids:
                bid_value = bid.get('value', {}).get('amount', 0)
                if bid_value and bid_value > 0:
                    bid_amounts.append(bid_value)
                
                for tenderer in bid.get('tenderers', []):
                    bid_id = tenderer.get('identifier', {}).get('id', '')
                    bid_name = tenderer.get('name', '')
                    if bid_id:
                        bidder_ids.append(bid_id)
                        bidder_names.append(bid_name)
            
            # Awards
            awards = tender.get('awards', [])
            winner_id = ''
            winner_name = ''
            award_amount = 0
            award_date = None
            
            for award in awards:
                if award.get('status') == 'active':
                    award_amount = award.get('value', {}).get('amount', 0)
                    award_date = award.get('date')
                    for supplier in award.get('suppliers', []):
                        winner_id = supplier.get('identifier', {}).get('id', '')
                        winner_name = supplier.get('name', '')
                    break
            
            # Skip invalid tenders
            if expected_value <= 0:
                return None
            
            return {
                'prozorro_id': tender_id,
                'status': status,
                'procurement_method': procurement_method,
                'procurement_method_type': procurement_method_type,
                'title': tender.get('title', ''),
                'description': tender.get('description', ''),
                'expected_value': expected_value,
                'currency': currency,
                'buyer_name': buyer_name,
                'buyer_id': buyer_id,
                'buyer_region': buyer_region if buyer_region else 'Unknown',
                'cpv_code': cpv_code,
                'cpv_description': cpv_description,
                'date_modified': date_modified,
                'start_date': start_date,
                'end_date': end_date,
                'num_bids': num_bids,
                'bid_amounts': bid_amounts if bid_amounts else [expected_value],
                'bidder_ids': bidder_ids,
                'bidder_names': bidder_names,
                'winner_id': winner_id,
                'winner_name': winner_name,
                'award_amount': award_amount if award_amount > 0 else expected_value,
                'award_date': award_date,
                'raw_data': tender,
            }
            
        except Exception as e:
            logger.error(f"Error parsing tender: {e}")
            return None
    
    def parse_tenders_batch(self, tenders: List[Dict]) -> List[Dict]:
        """Parse multiple tenders."""
        parsed = []
        for tender in tenders:
            result = self.parse_tender(tender)
            if result:
                parsed.append(result)
        return parsed


# Factory function
async def get_prozorro_client() -> ProzorroClient:
    """Get Prozorro client instance."""
    return ProzorroClient()
