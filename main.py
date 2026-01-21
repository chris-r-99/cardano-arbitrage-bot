#!/usr/bin/env python3
"""
Cardano Arbitrage Bot - Infrastructure Test

This script tests the connection to your Ogmios/cardano-node setup.

Usage:
    python main.py
"""

import asyncio
import logging
import sys

from config import settings
from core.blockchain import OgmiosClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_infrastructure() -> bool:
    """
    Test the infrastructure setup:
    1. Connect to Ogmios
    2. Query chain tip
    3. Verify connection health
    """
    print("=" * 60)
    print("Cardano Arbitrage Bot - Infrastructure Test")
    print("=" * 60)
    print()
    
    # Show configuration
    print(f"Ogmios URL: {settings.ogmios_url}")
    print()
    
    # Create client
    client = OgmiosClient(
        url=settings.ogmios_url,
        username=settings.ogmios_username,
        password=settings.ogmios_password,
    )
    
    # Test 1: Connection
    print("[1/3] Testing Ogmios connection...")
    connected = await client.connect()
    if not connected:
        print("❌ FAILED: Could not connect to Ogmios")
        print()
        print("Troubleshooting:")
        print("  1. Is cardano-node running?")
        print("  2. Is Ogmios running and connected to the node?")
        print(f"  3. Is Ogmios accessible at {settings.ogmios_url}?")
        print("  4. Check firewall/network settings")
        return False
    print("✅ Connected to Ogmios")
    
    try:
        # Test 2: Chain tip
        print()
        print("[2/3] Querying chain tip...")
        tip = await client.get_chain_tip()
        print(f"✅ Chain tip retrieved:")
        print(f"   Slot: {tip.slot:,}")
        print(f"   Block hash: {tip.block_hash[:16]}...")
        if tip.block_height:
            print(f"   Block height: {tip.block_height:,}")
        
        # Test 3: Health check
        print()
        print("[3/3] Running health check...")
        health = await client.health_check()
        if health["status"] == "healthy":
            print("✅ Health check passed")
        else:
            print(f"⚠️  Health check: {health}")
        
        print()
        print("=" * 60)
        print("✅ All infrastructure tests passed!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Run tests: pytest tests/test_ogmios.py -v")
        print("  2. Add DEX support (copy from existing repos)")
        print("  3. Implement pool fetching")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        logger.exception("Test failed with exception")
        return False
        
    finally:
        await client.disconnect()


async def main():
    """Main entry point"""
    try:
        success = await test_infrastructure()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
