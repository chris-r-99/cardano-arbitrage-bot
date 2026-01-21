"""Minswap V1 pool implementation - constant product AMM with 0.3% fee."""

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar, Optional

from pycardano import PlutusData

from core.types import Token
from .base import BasePool, BasePoolHandler

# Constants
POOL_TYPE = "minswap-v1"
POOL_SCRIPT_HASH = "e1317b152faac13426e6a83e06ff88a4d62cce3c1634ab0a5ec13309"
POOL_NFT_POLICY = "0be55d262b29f564998ff81efe21bdc0022621c12f15af08d0f2ddb1"
POOL_TOKEN_POLICY = "13aa2accf2e1561723aa26871e071fdf32c867cff7e7d50ad470d62f"
LP_TOKEN_POLICY = "e4214b7cce62ac6fbba385d164df48e157eae5863521b4b67ca71d86"
FEE_NUM, FEE_DEN = 997, 1000  # 0.3% fee


# Datum structures
@dataclass
class PoolToken(PlutusData):
    """Token in pool datum."""
    policy_id: bytes
    token_name: bytes
    CONSTR_ID: ClassVar[int] = 0

@dataclass
class MinswapV1PoolDatum(PlutusData):
    """Pool datum: token_a, token_b, total_liquidity, root_k_last."""
    token_a: PoolToken
    token_b: PoolToken
    total_liquidity: int
    root_k_last: int
    CONSTR_ID: ClassVar[int] = 0


@dataclass
class MinswapV1Pool(BasePool):
    """Minswap V1 constant product AMM pool (x * y = k)."""
    POOL_TYPE: ClassVar[str] = POOL_TYPE
    FEE: ClassVar[Decimal] = Decimal("0.3")
    
    def pool_out(self, input_token: Token, input_amount: int) -> int:
        """output = (input * 997 * reserve_out) / (reserve_in * 1000 + input * 997)"""
        r_in, r_out = self.get_reserves(input_token)
        amt_with_fee = input_amount * FEE_NUM
        return (amt_with_fee * r_out) // (r_in * FEE_DEN + amt_with_fee)
    
    def pool_in(self, output_token: Token, output_amount: int) -> int:
        """input = (reserve_in * output * 1000) / ((reserve_out - output) * 997) + 1"""
        if output_token == self.token_a:
            r_in, r_out = self.reserve_b, self.reserve_a
        elif output_token == self.token_b:
            r_in, r_out = self.reserve_a, self.reserve_b
        else:
            raise ValueError(f"Token {output_token} not in pool")
        
        if output_amount >= r_out:
            return int(1e18)
        return (r_in * output_amount * FEE_DEN) // ((r_out - output_amount) * FEE_NUM) + 1


class MinswapV1PoolHandler(BasePoolHandler):
    """Handler for Minswap V1 pools."""
    POOL_TYPE: ClassVar[str] = POOL_TYPE
    SCRIPT_HASHES: ClassVar[list] = [POOL_SCRIPT_HASH]
    NFT_POLICIES: ClassVar[list] = [POOL_NFT_POLICY]
    IGNORED_POLICIES: ClassVar[list] = [POOL_TOKEN_POLICY, LP_TOKEN_POLICY]
    
    def parse_datum(self, datum_cbor: bytes) -> MinswapV1PoolDatum:
        return MinswapV1PoolDatum.from_cbor(datum_cbor)
    
    def create_pool(self, utxo: dict, datum: MinswapV1PoolDatum, utxo_id: str) -> Optional[MinswapV1Pool]:
        token_a = Token(policy_id=datum.token_a.policy_id.hex(), name=datum.token_a.token_name.hex())
        token_b = Token(policy_id=datum.token_b.policy_id.hex(), name=datum.token_b.token_name.hex())
        
        pool_id = self.extract_pool_nft_id(utxo)
        if not pool_id:
            return None
        
        reserve_a, reserve_b = self.extract_reserves(utxo, token_a, token_b)
        if reserve_a == 0 or reserve_b == 0:
            return None
        
        return MinswapV1Pool(
            pool_id=pool_id, token_a=token_a, token_b=token_b,
            reserve_a=reserve_a, reserve_b=reserve_b, utxo_id=utxo_id,
        )


handler = MinswapV1PoolHandler()
