"""Pool handlers for all supported DEXes."""

from typing import Dict, List, Optional

from .base import Pool, PoolHandler, BasePool, BasePoolHandler
from .minswap_v1 import (
    MinswapV1Pool, MinswapV1PoolHandler, MinswapV1PoolDatum,
    handler as minswap_v1_handler,
    POOL_SCRIPT_HASH as MINSWAP_V1_SCRIPT,
    POOL_NFT_POLICY as MINSWAP_V1_NFT,
)

# Handler registry
HANDLERS: Dict[str, PoolHandler] = {
    "minswap-v1": minswap_v1_handler,
}

# Build script/NFT → type mappings
_SCRIPT_TO_TYPE = {s: t for t, h in HANDLERS.items() for s in h.script_hashes}
_NFT_TO_TYPE = {n: t for t, h in HANDLERS.items() for n in h.nft_policies}


def get_handler(pool_type: str) -> Optional[PoolHandler]:
    return HANDLERS.get(pool_type)

def get_handler_for_script(script_hash: str) -> Optional[PoolHandler]:
    return HANDLERS.get(_SCRIPT_TO_TYPE.get(script_hash))

def get_handler_for_nft(policy_id: str) -> Optional[PoolHandler]:
    return HANDLERS.get(_NFT_TO_TYPE.get(policy_id))

def all_handlers() -> List[PoolHandler]:
    return list(HANDLERS.values())

def all_script_hashes() -> List[str]:
    return list(_SCRIPT_TO_TYPE.keys())

def all_nft_policies() -> List[str]:
    return list(_NFT_TO_TYPE.keys())


__all__ = [
    "Pool", "PoolHandler", "BasePool", "BasePoolHandler",
    "MinswapV1Pool", "MinswapV1PoolHandler", "MinswapV1PoolDatum",
    "HANDLERS", "get_handler", "get_handler_for_script", "get_handler_for_nft",
    "all_handlers", "all_script_hashes", "all_nft_policies",
]
