#!/usr/bin/env python3
"""Test block-by-block syncing from latest blocks."""

import asyncio
import logging
import sys

from config import settings
from core.blockchain import OgmiosClient
from core.sync import BlockIterator, BlockProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_latest_blocks(num_blocks: int = 5):
    """Process the latest N blocks."""
    print("=" * 60)
    print(f"Testing Block Sync - Latest {num_blocks} Blocks")
    print("=" * 60)
    print()
    
    ogmios = OgmiosClient(url=settings.ogmios_url)
    if not await ogmios.connect():
        print("❌ Failed to connect to Ogmios")
        return False
    
    try:
        # Get chain tip
        tip = await ogmios.get_chain_tip()
        print(f"Chain tip: slot {tip.slot:,}, height {tip.block_height:,}")
        print()
        
        # Initialize block iterator (starts from tip)
        iterator = BlockIterator(ogmios)
        await iterator.init_connection()  # Start from latest
        
        # Process blocks
        processor = BlockProcessor()
        
        print(f"Processing {num_blocks} blocks...")
        print()
        
        async for block in iterator.iterate_blocks(max_blocks=num_blocks):
            result = processor.process_block(block)
            
            print(f"Block {result['block']['height']} (slot {result['block']['slot']:,})")
            print(f"  Orders: {len(result['orders'])}")
            print(f"  Pools: {len(result['pools'])}")
            
            if result['orders']:
                print("  Sample orders:")
                for order in result['orders'][:3]:
                    print(f"    - {order['bid_token'][:16]} → {order['ask_token'][:16]}: "
                          f"{order['bid_amount']:,} → {order['ask_amount']:,}")
            
            if result['pools']:
                print("  Sample pools:")
                for pool in result['pools'][:3]:
                    print(f"    - {pool['token_a'][:16]}/{pool['token_b'][:16]}: "
                          f"{pool['reserve_a']:,}/{pool['reserve_b']:,}")
            
            print()
        
        # Print summary
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Blocks processed: {processor.stats['blocks_processed']}")
        print(f"Transactions: {processor.stats['transactions_processed']}")
        print(f"Orders found: {processor.stats['orders_found']}")
        print(f"Pools found: {processor.stats['pools_found']}")
        print()
        print("✅ Sync test completed")
        print()
        print("Next steps:")
        print("  1. Add database models (Order, Pool, Tx)")
        print("  2. Write results to database")
        print("  3. Implement continuous syncing")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Sync failed")
        return False
    finally:
        await ogmios.disconnect()


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--num-blocks", type=int, default=5, help="Number of blocks to process")
    args = parser.parse_args()
    
    await test_latest_blocks(args.num_blocks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
