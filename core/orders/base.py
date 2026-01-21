"""Base classes for orders and parsers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, List, Optional, Protocol, runtime_checkable

from pycardano import PlutusData, Address, Redeemer, TransactionOutput, Value

from core.types import Token, Asset
from core.pools.base import Pool


@dataclass
class ExecutionResult:
    """Result of simulating order execution against a pool."""
    output_amount: int
    satisfies_min: bool
    profit_vs_min: int


@runtime_checkable
class Order(Protocol):
    """Protocol for order type checking."""
    order_id: str
    order_type: str
    utxo_id: str
    bid_asset: Asset
    ask_asset: Asset
    batcher_fee: int
    deposit: int
    sender: tuple[str, Optional[str]]
    beneficiary: tuple[str, Optional[str]]
    target_pool_id: Optional[str]
    
    @property
    def bid_token(self) -> Token: ...
    @property
    def ask_token(self) -> Token: ...
    def can_match_pool(self, pool: Pool) -> bool: ...
    def simulate(self, pool: Pool) -> ExecutionResult: ...
    def would_satisfy(self, pool: Pool) -> bool: ...


@dataclass
class BaseOrder(ABC):
    """
    Base class for DEX orders.
    
    Subclasses must set ORDER_TYPE and POOL_TYPE class attributes.
    """
    ORDER_TYPE: ClassVar[str] = ""
    POOL_TYPE: ClassVar[str] = ""
    
    order_id: str
    bid_asset: Asset
    ask_asset: Asset
    batcher_fee: int
    deposit: int
    sender: tuple[str, Optional[str]]
    beneficiary: tuple[str, Optional[str]]
    utxo_id: str
    target_pool_id: Optional[str] = None
    
    @property
    def order_type(self) -> str:
        return self.ORDER_TYPE
    
    @property
    def bid_token(self) -> Token:
        return self.bid_asset.token
    
    @property
    def ask_token(self) -> Token:
        return self.ask_asset.token
    
    @property
    def fee_and_deposit(self) -> int:
        return self.batcher_fee + self.deposit
    
    def can_match_pool(self, pool: Pool) -> bool:
        """Check if order can match with pool (type and token pair)."""
        if pool.pool_type != self.POOL_TYPE:
            return False
        return {pool.token_a, pool.token_b} == {self.bid_token, self.ask_token}
    
    def simulate(self, pool: Pool) -> ExecutionResult:
        """Simulate execution against a pool."""
        output = pool.pool_out(self.bid_token, self.bid_asset.amount)
        return ExecutionResult(output, output >= self.ask_asset.amount, output - self.ask_asset.amount)
    
    def would_satisfy(self, pool: Pool) -> bool:
        """Check if execution would meet minimum output."""
        return self.can_match_pool(pool) and self.simulate(pool).satisfies_min
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.bid_asset} → {self.ask_asset})"


class OrderParser(Protocol):
    """Protocol for order parsers."""
    order_type: str
    script_hashes: List[str]
    
    def is_order_utxo(self, utxo: dict) -> bool: ...
    def parse_order(self, utxo: dict, datum_cbor: bytes, utxo_id: str) -> Optional["BaseOrder"]: ...


class BaseOrderParser(ABC):
    """
    Base class for order parsers.
    
    Subclasses must set ORDER_TYPE/SCRIPT_HASHES and implement parse_datum()/create_order().
    """
    ORDER_TYPE: ClassVar[str] = ""
    SCRIPT_HASHES: ClassVar[List[str]] = []
    
    @property
    def order_type(self) -> str:
        return self.ORDER_TYPE
    
    @property
    def script_hashes(self) -> List[str]:
        return self.SCRIPT_HASHES
    
    def is_order_utxo(self, utxo: dict) -> bool:
        """Check if UTxO is an order based on script hash."""
        script_hash = utxo.get("script_hash") or utxo.get("address_script_hash", "")
        return script_hash in self.SCRIPT_HASHES
    
    def parse_order(self, utxo: dict, datum_cbor: bytes, utxo_id: str) -> Optional[BaseOrder]:
        """Parse order from UTxO and datum CBOR. Returns None if parsing fails."""
        try:
            return self.create_order(utxo, self.parse_datum(datum_cbor), utxo_id)
        except Exception:
            return None
    
    @abstractmethod
    def parse_datum(self, datum_cbor: bytes) -> PlutusData: ...
    
    @abstractmethod
    def create_order(self, utxo: dict, datum: PlutusData, utxo_id: str) -> BaseOrder: ...
    
    def extract_bid_asset_from_utxo(
        self, 
        utxo: dict, 
        subtract_lovelace: int,
        ignore_policies: Optional[List[str]] = None,
    ) -> Asset:
        """Extract bid asset from UTxO (highest amount non-ADA token, or ADA minus fees)."""
        value = utxo.get("value", {})
        ada_amount = value.get("ada", {}).get("lovelace", 0)
        ignore_policies = ignore_policies or []
        
        # Collect non-ADA assets
        non_ada = [
            Asset(amount=amt, token=Token(policy_id=pid, name=name))
            for pid, assets in value.items()
            if pid != "ada" and pid not in ignore_policies
            for name, amt in assets.items()
            if amt > 0
        ]
        
        if non_ada:
            return max(non_ada, key=lambda a: a.amount)
        return Asset(amount=max(0, ada_amount - subtract_lovelace), token=Token.ada())


@dataclass
class CancellationInputs:
    """Inputs needed to cancel an order."""
    redeemer: Redeemer
    datum: PlutusData
    output: TransactionOutput
    script: object


class OrderCanceller(ABC):
    """Base for order cancellation support."""
    
    @abstractmethod
    def get_cancellation_inputs(self, user_address: Address, order: dict, output_value: Value) -> CancellationInputs: ...
    
    @abstractmethod
    def create_cancellation_redeemer(self) -> Redeemer: ...
