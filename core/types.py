"""
Core types for the arbitrage bot.

Minimal Token and Asset types. Uses pycardano for everything else.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Token:
    """
    Represents a Cardano native token.
    
    ADA is represented with empty policy_id and name.
    Name is stored as hex (not decoded).
    """
    policy_id: str
    name: str  # hex encoded
    
    @property
    def is_ada(self) -> bool:
        return self.policy_id == "" and self.name == ""
    
    @classmethod
    def ada(cls) -> "Token":
        return cls(policy_id="", name="")
    
    @classmethod
    def from_hex(cls, hex_str: str) -> "Token":
        """
        Create from concatenated hex string (policy_id + name).
        Policy ID is always 56 hex chars (28 bytes).
        """
        if not hex_str or hex_str == "lovelace" or hex_str == ".":
            return cls.ada()
        # Handle format with dot separator
        if "." in hex_str:
            hex_str = hex_str.replace(".", "")
        if len(hex_str) <= 56:
            return cls(policy_id=hex_str, name="")
        return cls(policy_id=hex_str[:56], name=hex_str[56:])
    
    def __str__(self) -> str:
        if self.is_ada:
            return "ADA"
        try:
            decoded = bytes.fromhex(self.name).decode("utf-8")
            return f"{self.policy_id[:8]}..{decoded}"
        except (ValueError, UnicodeDecodeError):
            return f"{self.policy_id[:8]}..{self.name[:8]}"
    
    def __repr__(self) -> str:
        if self.is_ada:
            return "Token(ADA)"
        return f"Token({self.policy_id[:8]}..{self.name[:8] if self.name else ''})"


@dataclass(frozen=True)
class Asset:
    """Token with amount."""
    amount: int
    token: Token
    
    def __str__(self) -> str:
        return f"{self.amount} {self.token}"


# Common tokens
ADA = Token.ada()
