"""Chain client protocol for fetching UTxOs."""

from typing import Protocol, List, Optional


class ChainClient(Protocol):
    """
    Interface for chain data providers (Ogmios, Blockfrost, Kupo, etc.).
    
    UTxO dict structure:
        {"tx_hash": str, "output_index": int, "value": {...},
         "datum_cbor": Optional[str], "datum_hash": Optional[str], "script_hash": Optional[str]}
    """
    
    async def get_utxos_by_scripts(self, script_hashes: List[str]) -> List[dict]:
        """Fetch UTxOs at script addresses."""
        ...
    
    async def get_datum(self, datum_hash: str) -> Optional[bytes]:
        """Fetch datum CBOR by hash."""
        ...
    
    async def get_utxos_by_nft(self, policy_id: str) -> List[dict]:
        """Fetch UTxOs containing a specific NFT policy."""
        ...
