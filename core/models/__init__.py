"""
Data models for the arbitrage bot
"""

from dataclasses import dataclass
from typing import Optional
from decimal import Decimal


@dataclass
class Token:
    """Represents a Cardano native token"""
    policy_id: str
    asset_name: str
    
    @property
    def subject(self) -> str:
        """Full token identifier (policy_id + asset_name)"""
        return f"{self.policy_id}{self.asset_name}"
    
    @property
    def is_ada(self) -> bool:
        """Check if this is ADA (lovelace)"""
        return self.policy_id == "" and self.asset_name == ""
    
    @classmethod
    def ada(cls) -> "Token":
        """Create ADA token"""
        return cls(policy_id="", asset_name="")
    
    @classmethod
    def from_subject(cls, subject: str) -> "Token":
        """Create token from subject string"""
        if not subject or subject == "lovelace":
            return cls.ada()
        # Policy ID is 56 hex chars (28 bytes)
        policy_id = subject[:56]
        asset_name = subject[56:]
        return cls(policy_id=policy_id, asset_name=asset_name)


@dataclass
class Pool:
    """Represents a DEX liquidity pool"""
    pool_id: str
    dex: str
    token_a: Token
    token_b: Token
    reserve_a: int
    reserve_b: int
    fee: Decimal  # Pool fee as decimal (e.g., 0.003 for 0.3%)
    
    @property
    def price_a_to_b(self) -> Decimal:
        """Price of token A in terms of token B"""
        if self.reserve_a == 0:
            return Decimal(0)
        return Decimal(self.reserve_b) / Decimal(self.reserve_a)
    
    @property
    def price_b_to_a(self) -> Decimal:
        """Price of token B in terms of token A"""
        if self.reserve_b == 0:
            return Decimal(0)
        return Decimal(self.reserve_a) / Decimal(self.reserve_b)


@dataclass
class ArbitrageOpportunity:
    """Represents a potential arbitrage opportunity"""
    token_pair: tuple[Token, Token]
    buy_pool: Pool
    sell_pool: Pool
    expected_profit: int  # In lovelace
    buy_price: Decimal
    sell_price: Decimal
    timestamp: Optional[float] = None
