"""Minswap V1 order implementation."""

from dataclasses import dataclass
from typing import ClassVar, Optional, Union

from pycardano import PlutusData, Address, Redeemer, PlutusV1Script, TransactionOutput, Value

from core.types import Token, Asset
from .base import BaseOrder, BaseOrderParser, CancellationInputs
from .plutus_common import from_hex, StakingOuter, PlutusAddress, create_plutus_address

# Constants
ORDER_TYPE = "minswap-v1"
ORDER_SCRIPT_HASH = "c620c56751448d1a92184c8f506a4d1f31fc53e55fdd694c8bcda6fa"
ORDER_ADDRESS = "addr1zxn9efv2f6w82hagxqtn62ju4m293tqvw0uhmdl64ch8uw6j2c79gy9l76sdg0xwhd7r0c0kna0tycz4y5s6mlenh8pq6s3z70"
BATCHER_FEE_DEFAULT = 900_000
DEPOSIT_DEFAULT = 2_500_000


# Datum structures
@dataclass
class BuyToken(PlutusData):
    policy_id: bytes
    token_name: bytes
    CONSTR_ID: ClassVar[int] = 0

@dataclass
class BuyAsset(PlutusData):
    token: BuyToken
    amount: int
    CONSTR_ID: ClassVar[int] = 0

@dataclass
class EmptyDatum(PlutusData):
    """Empty datum for optional fields and cancellation redeemer."""
    CONSTR_ID: ClassVar[int] = 1

@dataclass
class MinswapV1OrderDatum(PlutusData):
    """Order datum: sender, receiver, datum_hash, buy_asset, fee, deposit."""
    sender_address: PlutusAddress
    receiver_address: PlutusAddress
    optional_receiver_datum_hash: Union[PlutusData, EmptyDatum]
    buy_asset: BuyAsset
    batcher_fee: int
    deposit: int
    CONSTR_ID: ClassVar[int] = 0


@dataclass
class MinswapV1Order(BaseOrder):
    """Minswap V1 swap order."""
    ORDER_TYPE: ClassVar[str] = ORDER_TYPE
    POOL_TYPE: ClassVar[str] = "minswap-v1"


class MinswapV1OrderParser(BaseOrderParser):
    """Parser for Minswap V1 orders."""
    ORDER_TYPE: ClassVar[str] = ORDER_TYPE
    SCRIPT_HASHES: ClassVar[list] = [ORDER_SCRIPT_HASH]
    
    def parse_datum(self, datum_cbor: bytes) -> MinswapV1OrderDatum:
        return MinswapV1OrderDatum.from_cbor(datum_cbor)
    
    def create_order(self, utxo: dict, datum: MinswapV1OrderDatum, utxo_id: str) -> MinswapV1Order:
        sender = self._extract_address(datum.sender_address)
        beneficiary = self._extract_address(datum.receiver_address)
        
        ask_token = Token(
            policy_id=datum.buy_asset.token.policy_id.hex(),
            name=datum.buy_asset.token.token_name.hex()
        )
        bid_asset = self.extract_bid_asset_from_utxo(utxo, datum.batcher_fee + datum.deposit)
        
        return MinswapV1Order(
            order_id=utxo_id, bid_asset=bid_asset,
            ask_asset=Asset(amount=datum.buy_asset.amount, token=ask_token),
            batcher_fee=datum.batcher_fee, deposit=datum.deposit,
            sender=sender, beneficiary=beneficiary, utxo_id=utxo_id,
        )
    
    def _extract_address(self, addr: PlutusAddress) -> tuple[str, Optional[str]]:
        pkh = addr.pub_key_hash.pub_key_hash.hex()
        skh = addr.staking_outer.staking_inner.staking_cred_hash.staking_cred_hash.hex() \
            if isinstance(addr.staking_outer, StakingOuter) else None
        return (pkh, skh)


parser = MinswapV1OrderParser()


# Order creation helper
def create_order_datum(
    user_address: Address,
    buy_token: Token,
    buy_amount: int,
    batcher_fee: int = BATCHER_FEE_DEFAULT,
    deposit: int = DEPOSIT_DEFAULT,
) -> MinswapV1OrderDatum:
    """Create a Minswap V1 order datum for transaction building."""
    addr = create_plutus_address(user_address)
    return MinswapV1OrderDatum(
        sender_address=addr,
        receiver_address=addr,
        optional_receiver_datum_hash=EmptyDatum(),
        buy_asset=BuyAsset(
            token=BuyToken(policy_id=from_hex(buy_token.policy_id), token_name=from_hex(buy_token.name)),
            amount=int(buy_amount),
        ),
        batcher_fee=int(batcher_fee),
        deposit=int(deposit),
    )


# Cancellation support
def create_cancellation_redeemer() -> Redeemer:
    return Redeemer(data=EmptyDatum())


def get_cancellation_inputs(user_address: Address, order: dict, output_value: Value) -> CancellationInputs:
    """Get inputs needed to cancel a Minswap V1 order."""
    return CancellationInputs(
        redeemer=create_cancellation_redeemer(),
        datum=create_order_datum(user_address, Token.from_hex(order["toToken"]), order["toAmount"]),
        output=TransactionOutput(address=Address.decode(ORDER_ADDRESS), amount=output_value),
        script=CBOR_SCRIPT,
    )


# Minswap V1 order contract script
CBOR_SCRIPT = PlutusV1Script(bytes.fromhex(
    "59014c01000032323232323232322223232325333009300e30070021323233533300b3370e9000180480109118011bae30100031225001232533300d3300e22533301300114a02a66601e66ebcc04800400c5288980118070009bac3010300c300c300c300c300c300c300c007149858dd48008b18060009baa300c300b3754601860166ea80184ccccc0288894ccc04000440084c8c94ccc038cd4ccc038c04cc030008488c008dd718098018912800919b8f0014891ce1317b152faac13426e6a83e06ff88a4d62cce3c1634ab0a5ec133090014a0266008444a00226600a446004602600a601a00626600a008601a006601e0026ea8c03cc038dd5180798071baa300f300b300e3754601e00244a0026eb0c03000c92616300a001375400660106ea8c024c020dd5000aab9d5744ae688c8c0088cc0080080048c0088cc00800800555cf2ba15573e6e1d200201"
))
