"""Ogmios adapter implementing ChainClient protocol."""

from typing import List, Optional, Dict
import logging

from core.blockchain import OgmiosClient

logger = logging.getLogger(__name__)


class OgmiosChainClient:
    """
    Wraps OgmiosClient to provide ChainClient interface.
    
    Ogmios queries by address, so script_hash → address mappings must be registered.
    """
    
    def __init__(self, ogmios: OgmiosClient):
        self.ogmios = ogmios
        self._script_to_address: Dict[str, str] = {}
    
    def register_address(self, script_hash: str, address: str):
        """Register script hash → address mapping."""
        self._script_to_address[script_hash] = address
    
    async def get_utxos_by_scripts(self, script_hashes: List[str]) -> List[dict]:
        """Fetch UTxOs at registered script addresses."""
        utxos = []
        for script_hash in script_hashes:
            if address := self._script_to_address.get(script_hash):
                raw = await self.ogmios.get_utxos_by_address(address)
                utxos.extend(self._convert(raw, script_hash))
        return utxos
    
    async def get_utxos_by_nft(self, policy_id: str) -> List[dict]:
        """Not supported by Ogmios - use Kupo."""
        logger.debug(f"get_utxos_by_nft requires Kupo: {policy_id[:16]}...")
        return []
    
    async def get_datum(self, datum_hash: str) -> Optional[bytes]:
        """Not supported - use inline datums."""
        return None
    
    def _convert(self, ogmios_utxos: List[dict], script_hash: str) -> List[dict]:
        """Convert Ogmios UTxO format to standard format."""
        return [{
            "tx_hash": u.get("transaction", {}).get("id", ""),
            "output_index": u.get("index", 0),
            "address": u.get("address", ""),
            "value": u.get("value", {}),
            "datum_cbor": u.get("datum"),
            "datum_hash": u.get("datumHash"),
            "script_hash": script_hash,
        } for u in ogmios_utxos]
