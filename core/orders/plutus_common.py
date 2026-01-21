"""Common Plutus datum structures shared across DEX implementations."""

from dataclasses import dataclass
from typing import ClassVar, Union

from pycardano import PlutusData, Address


def from_hex(hex_string: str) -> bytes:
    """Convert hex string to bytes. Returns empty bytes for empty/None input."""
    return bytes.fromhex(hex_string) if hex_string else b""


# Common Plutus structures
@dataclass
class EmptyDatum(PlutusData):
    """Empty datum for 'Nothing' in optional fields."""
    CONSTR_ID: ClassVar[int] = 0

@dataclass
class PlutusTrue(PlutusData):
    CONSTR_ID: ClassVar[int] = 0

@dataclass
class PlutusFalse(PlutusData):
    CONSTR_ID: ClassVar[int] = 1


# Address components
@dataclass
class PubKeyHash(PlutusData):
    """Public key hash (28 bytes)."""
    pub_key_hash: bytes
    CONSTR_ID: ClassVar[int] = 0

@dataclass
class StakingCredentialHash(PlutusData):
    """Staking credential hash (28 bytes)."""
    staking_cred_hash: bytes
    CONSTR_ID: ClassVar[int] = 0

@dataclass
class StakingInner(PlutusData):
    """Inner wrapper: StakingHash (PubKeyCredential hash)."""
    CONSTR_ID: ClassVar[int] = 0
    staking_cred_hash: StakingCredentialHash

@dataclass
class StakingOuter(PlutusData):
    """Outer wrapper: Just (StakingHash credential)."""
    staking_inner: StakingInner
    CONSTR_ID: ClassVar[int] = 0

@dataclass
class NoStakingCredential(PlutusData):
    """No staking credential (Nothing)."""
    CONSTR_ID: ClassVar[int] = 1

@dataclass
class PlutusAddress(PlutusData):
    """Full Plutus address with payment and optional staking credentials."""
    pub_key_hash: PubKeyHash
    staking_outer: Union[StakingOuter, NoStakingCredential]
    CONSTR_ID: ClassVar[int] = 0

@dataclass
class PlutusToken(PlutusData):
    """On-chain token (policy ID + asset name). Empty bytes for ADA."""
    policy_id: bytes
    token_name: bytes
    CONSTR_ID: ClassVar[int] = 0


# Helper functions
def create_staking_credential(address: Address) -> Union[StakingOuter, NoStakingCredential]:
    """Create staking credential wrapper from PyCardano Address."""
    if address.staking_part:
        return StakingOuter(StakingInner(StakingCredentialHash(address.staking_part.to_primitive())))
    return NoStakingCredential()


def create_plutus_address(address: Address) -> PlutusAddress:
    """Create PlutusAddress from PyCardano Address."""
    return PlutusAddress(
        pub_key_hash=PubKeyHash(pub_key_hash=address.payment_part.to_primitive()),
        staking_outer=create_staking_credential(address),
    )


def create_plutus_token(policy_id: str, token_name: str) -> PlutusToken:
    """Create PlutusToken from hex strings."""
    return PlutusToken(policy_id=from_hex(policy_id), token_name=from_hex(token_name))
