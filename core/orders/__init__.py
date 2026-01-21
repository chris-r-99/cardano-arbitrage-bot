"""Order parsers for all supported DEXes."""

from typing import Dict, List, Optional

from .base import Order, OrderParser, BaseOrder, BaseOrderParser, ExecutionResult, CancellationInputs
from .plutus_common import (
    PlutusAddress, PlutusToken, PubKeyHash, StakingOuter, NoStakingCredential,
    create_plutus_address, create_plutus_token, from_hex,
)
from .minswap_v1 import (
    MinswapV1Order, MinswapV1OrderParser, MinswapV1OrderDatum,
    parser as minswap_v1_parser,
    ORDER_SCRIPT_HASH as MINSWAP_V1_ORDER_SCRIPT,
    create_order_datum as create_minswap_v1_order_datum,
)

# Parser registry
PARSERS: Dict[str, OrderParser] = {
    "minswap-v1": minswap_v1_parser,
}

# Build script → type mapping
_SCRIPT_TO_TYPE = {s: t for t, p in PARSERS.items() for s in p.script_hashes}


def get_parser(order_type: str) -> Optional[OrderParser]:
    return PARSERS.get(order_type)

def get_parser_for_script(script_hash: str) -> Optional[OrderParser]:
    return PARSERS.get(_SCRIPT_TO_TYPE.get(script_hash))

def all_parsers() -> List[OrderParser]:
    return list(PARSERS.values())

def all_script_hashes() -> List[str]:
    return list(_SCRIPT_TO_TYPE.keys())


__all__ = [
    "Order", "OrderParser", "BaseOrder", "BaseOrderParser", "ExecutionResult", "CancellationInputs",
    "PlutusAddress", "PlutusToken", "PubKeyHash", "StakingOuter", "NoStakingCredential",
    "create_plutus_address", "create_plutus_token", "from_hex",
    "MinswapV1Order", "MinswapV1OrderParser", "MinswapV1OrderDatum", "create_minswap_v1_order_datum",
    "PARSERS", "get_parser", "get_parser_for_script", "all_parsers", "all_script_hashes",
]
