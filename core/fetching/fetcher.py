"""Pool and order fetching from chain."""

from typing import List, Optional
import logging

from core.types import Token
from core.pools import get_handler, all_handlers
from core.pools.base import Pool, PoolHandler
from core.orders import get_parser, all_parsers
from core.orders.base import Order, OrderParser
from .client import ChainClient

logger = logging.getLogger(__name__)


class Fetcher:
    """Fetches pools and orders from chain using any ChainClient implementation."""
    
    def __init__(self, client: ChainClient):
        self.client = client
    
    async def fetch_pools(
        self,
        pool_types: Optional[List[str]] = None,
        token: Optional[Token] = None,
    ) -> List[Pool]:
        """Fetch pools, optionally filtered by type or token."""
        handlers = [h for h in (get_handler(t) for t in pool_types) if h] if pool_types else all_handlers()
        if not handlers:
            return []
        
        # Build NFT → handler lookup
        nft_to_handler = {nft: h for h in handlers for nft in h.nft_policies}
        
        pools = []
        for nft_policy, handler in nft_to_handler.items():
            for utxo in await self.client.get_utxos_by_nft(nft_policy):
                pool = await self._try_parse_pool(utxo, handler)
                if pool and (not token or pool.contains_token(token)):
                    pools.append(pool)
        return pools
    
    async def fetch_pools_for_pair(self, token_a: Token, token_b: Token) -> List[Pool]:
        """Fetch all pools for a specific token pair."""
        pair = {token_a, token_b}
        return [p for p in await self.fetch_pools() if {p.token_a, p.token_b} == pair]
    
    async def _try_parse_pool(self, utxo: dict, handler: PoolHandler) -> Optional[Pool]:
        if not handler.is_pool_utxo(utxo):
            return None
        datum_cbor = await self._get_datum_cbor(utxo)
        if not datum_cbor:
            return None
        try:
            return handler.parse_pool(utxo, datum_cbor, f"{utxo['tx_hash']}#{utxo['output_index']}")
        except Exception as e:
            logger.debug(f"Failed to parse pool: {e}")
            return None
    
    async def fetch_orders(self, order_types: Optional[List[str]] = None) -> List[Order]:
        """Fetch orders, optionally filtered by type."""
        parsers = [p for p in (get_parser(t) for t in order_types) if p] if order_types else all_parsers()
        if not parsers:
            return []
        
        # Build script → parser lookup
        script_to_parser = {s: p for p in parsers for s in p.script_hashes}
        utxos = await self.client.get_utxos_by_scripts(list(script_to_parser.keys()))
        
        orders = []
        for utxo in utxos:
            script = utxo.get("script_hash") or utxo.get("address_script_hash", "")
            if parser := script_to_parser.get(script):
                if order := await self._try_parse_order(utxo, parser):
                    orders.append(order)
        return orders
    
    async def fetch_orders_for_pair(self, token_a: Token, token_b: Token) -> List[Order]:
        """Fetch all orders for a specific token pair."""
        pair = {token_a, token_b}
        return [o for o in await self.fetch_orders() if {o.bid_token, o.ask_token} == pair]
    
    async def fetch_matchable_orders(self, pool: Pool) -> List[Order]:
        """Fetch orders that can be matched with a specific pool."""
        return [o for o in await self.fetch_orders() if o.can_match_pool(pool)]
    
    async def _try_parse_order(self, utxo: dict, parser: OrderParser) -> Optional[Order]:
        if not parser.is_order_utxo(utxo):
            return None
        datum_cbor = await self._get_datum_cbor(utxo)
        if not datum_cbor:
            return None
        try:
            return parser.parse_order(utxo, datum_cbor, f"{utxo['tx_hash']}#{utxo['output_index']}")
        except Exception as e:
            logger.debug(f"Failed to parse order: {e}")
            return None
    
    async def _get_datum_cbor(self, utxo: dict) -> Optional[bytes]:
        """Get datum CBOR from UTxO (inline or by hash)."""
        if utxo.get("datum_cbor"):
            return bytes.fromhex(utxo["datum_cbor"])
        if utxo.get("datum_hash"):
            return await self.client.get_datum(utxo["datum_hash"])
        return None
