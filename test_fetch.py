#!/usr/bin/env python3
"""Test fetching orders via Ogmios."""

import asyncio
import sys
import logging

from config import settings
from core.blockchain import OgmiosClient
from core.fetching import Fetcher, OgmiosChainClient
from core.orders.minswap_v1 import ORDER_SCRIPT_HASH, ORDER_ADDRESS

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    print("=" * 60)
    print("Testing Order Fetching via Ogmios")
    print("=" * 60)
    print()
    
    # Connect
    print(f"Connecting to Ogmios at {settings.ogmios_url}...")
    ogmios = OgmiosClient(
        url=settings.ogmios_url,
        username=settings.ogmios_username,
        password=settings.ogmios_password,
    )
    
    if not await ogmios.connect():
        print("❌ Failed to connect to Ogmios")
        print()
        print("Check:")
        print(f"  1. Is Ogmios running at {settings.ogmios_url}?")
        print("  2. Is cardano-node synced?")
        print("  3. Network/firewall settings?")
        return False
    
    print("✅ Connected to Ogmios")
    print()
    
    try:
        # Get chain tip
        tip = await ogmios.get_chain_tip()
        print(f"Chain tip: slot {tip.slot:,}")
        if tip.block_height:
            print(f"Block height: {tip.block_height:,}")
        print()
        
        # Setup adapter with Minswap V1 address
        print("Setting up Minswap V1 order contract...")
        client = OgmiosChainClient(ogmios)
        client.register_address(ORDER_SCRIPT_HASH, ORDER_ADDRESS)
        print(f"  Script hash: {ORDER_SCRIPT_HASH}")
        print(f"  Address: {ORDER_ADDRESS[:40]}...")
        print()
        
        # Fetch orders
        print("Fetching orders...")
        fetcher = Fetcher(client)
        orders = await fetcher.fetch_orders(order_types=["minswap-v1"])
        
        print()
        print(f"✅ Found {len(orders)} Minswap V1 orders")
        print()
        
        if orders:
            print("Sample orders (showing up to 10):")
            print("-" * 60)
            for i, order in enumerate(orders[:10], 1):
                bid = "ADA" if order.bid_token.is_ada else order.bid_token.name[:16]
                ask = "ADA" if order.ask_token.is_ada else order.ask_token.name[:16]
                price = order.bid_amount / order.ask_amount if order.ask_amount > 0 else 0
                print(f"{i}. {bid} → {ask}")
                print(f"   Bid: {order.bid_amount:,} | Ask: {order.ask_amount:,}")
                print(f"   Price: {price:.8f} {bid}/{ask}")
                print(f"   UTxO: {order.utxo_id[:50]}...")
                print()
        else:
            print("No orders found. This is normal if:")
            print("  - No pending Minswap V1 orders exist right now")
            print("  - All orders were recently matched")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Test failed")
        return False
        
    finally:
        await ogmios.disconnect()
        print("Disconnected from Ogmios")


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
