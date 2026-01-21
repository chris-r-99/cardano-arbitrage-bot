"""
Core module for the Cardano arbitrage bot.

Structure:
    core/
    ├── types.py          # Token, Asset
    ├── blockchain/       # Ogmios client
    ├── pools/            # Pool handlers
    ├── orders/           # Order parsers
    ├── fetching/         # Chain data fetching
    └── arbitrage/        # Arbitrage detection (TODO)

Usage:
    from core import Token, Asset, ADA
    from core.blockchain import OgmiosClient
    from core.pools import MinswapV1Pool, get_handler
    from core.orders import MinswapV1Order, get_parser
    from core.fetching import Fetcher
"""

from .types import Token, Asset, ADA

__all__ = [
    # Types
    "Token",
    "Asset", 
    "ADA",
]
