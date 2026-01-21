"""Base classes for pools and handlers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar, List, Optional, Protocol, runtime_checkable

from pycardano import PlutusData

from core.types import Token


@runtime_checkable
class Pool(Protocol):
    """Protocol for pool type checking."""
    pool_id: str
    pool_type: str
    utxo_id: str
    token_a: Token
    token_b: Token
    reserve_a: int
    reserve_b: int
    fee: Decimal
    
    def pool_out(self, input_token: Token, input_amount: int) -> int: ...
    def pool_in(self, output_token: Token, output_amount: int) -> int: ...
    def price(self, base_token: Token) -> Decimal: ...
    def contains_token(self, token: Token) -> bool: ...
    def other_token(self, token: Token) -> Token: ...


@dataclass
class BasePool(ABC):
    """Base class for DEX pools."""
    POOL_TYPE: ClassVar[str] = ""
    FEE: ClassVar[Decimal] = Decimal("0")
    
    pool_id: str
    token_a: Token
    token_b: Token
    reserve_a: int
    reserve_b: int
    utxo_id: str
    
    @property
    def pool_type(self) -> str:
        return self.POOL_TYPE
    
    @property
    def fee(self) -> Decimal:
        return self.FEE
    
    @abstractmethod
    def pool_out(self, input_token: Token, input_amount: int) -> int:
        """Calculate output amount for given input."""
        ...
    
    @abstractmethod
    def pool_in(self, output_token: Token, output_amount: int) -> int:
        """Calculate required input for desired output."""
        ...
    
    def price(self, base_token: Token) -> Decimal:
        """Spot price of quote token in terms of base token."""
        if base_token == self.token_a:
            return Decimal(self.reserve_b) / Decimal(self.reserve_a) if self.reserve_a else Decimal(0)
        if base_token == self.token_b:
            return Decimal(self.reserve_a) / Decimal(self.reserve_b) if self.reserve_b else Decimal(0)
        raise ValueError(f"Token {base_token} not in pool")
    
    def contains_token(self, token: Token) -> bool:
        return token == self.token_a or token == self.token_b
    
    def other_token(self, token: Token) -> Token:
        if token == self.token_a:
            return self.token_b
        if token == self.token_b:
            return self.token_a
        raise ValueError(f"Token {token} not in pool")
    
    def get_reserves(self, input_token: Token) -> tuple[int, int]:
        """Get (reserve_in, reserve_out) for given input token."""
        if input_token == self.token_a:
            return self.reserve_a, self.reserve_b
        if input_token == self.token_b:
            return self.reserve_b, self.reserve_a
        raise ValueError(f"Token {input_token} not in pool")


class PoolHandler(Protocol):
    """Protocol for pool handlers."""
    pool_type: str
    script_hashes: List[str]
    nft_policies: List[str]
    
    def is_pool_utxo(self, utxo: dict) -> bool: ...
    def parse_pool(self, utxo: dict, datum_cbor: bytes, utxo_id: str) -> Optional[Pool]: ...


class BasePoolHandler(ABC):
    """Base class for pool handlers."""
    POOL_TYPE: ClassVar[str] = ""
    SCRIPT_HASHES: ClassVar[List[str]] = []
    NFT_POLICIES: ClassVar[List[str]] = []
    IGNORED_POLICIES: ClassVar[List[str]] = []
    MIN_POOL_ADA: ClassVar[int] = 4_000_000
    
    @property
    def pool_type(self) -> str:
        return self.POOL_TYPE
    
    @property
    def script_hashes(self) -> List[str]:
        return self.SCRIPT_HASHES
    
    @property
    def nft_policies(self) -> List[str]:
        return self.NFT_POLICIES
    
    def extract_pool_nft_id(self, utxo: dict) -> Optional[str]:
        """Extract pool NFT asset name from UTxO (returns None if not a pool)."""
        value = utxo.get("value", {})
        for policy in self.NFT_POLICIES:
            if policy in value:
                for name, amount in value[policy].items():
                    if amount == 1:
                        return name
        return None
    
    def is_pool_utxo(self, utxo: dict) -> bool:
        """Check if UTxO is a pool (has NFT with amount 1)."""
        return self.extract_pool_nft_id(utxo) is not None
    
    def parse_pool(self, utxo: dict, datum_cbor: bytes, utxo_id: str) -> Optional[BasePool]:
        """Parse pool from UTxO and datum CBOR. Returns None if parsing fails."""
        try:
            return self.create_pool(utxo, self.parse_datum(datum_cbor), utxo_id)
        except Exception:
            return None
    
    @abstractmethod
    def parse_datum(self, datum_cbor: bytes) -> PlutusData: ...
    
    @abstractmethod
    def create_pool(self, utxo: dict, datum: PlutusData, utxo_id: str) -> Optional[BasePool]: ...
    
    def extract_reserves(self, utxo: dict, token_a: Token, token_b: Token) -> tuple[int, int]:
        """Extract (reserve_a, reserve_b) from UTxO value."""
        value = utxo.get("value", {})
        ada_amount = value.get("ada", {}).get("lovelace", 0)
        ignored = set(self.NFT_POLICIES + self.IGNORED_POLICIES)
        
        reserve_a, reserve_b = 0, 0
        for policy_id, assets in value.items():
            if policy_id == "ada" or policy_id in ignored:
                continue
            for asset_name, amount in assets.items():
                if policy_id == token_a.policy_id and asset_name == token_a.name:
                    reserve_a = amount
                elif policy_id == token_b.policy_id and asset_name == token_b.name:
                    reserve_b = amount
        
        # Handle ADA as token
        if token_a.is_ada and ada_amount >= self.MIN_POOL_ADA:
            reserve_a = ada_amount
        elif token_b.is_ada and ada_amount >= self.MIN_POOL_ADA:
            reserve_b = ada_amount
        
        return reserve_a, reserve_b
