"""Block iterator using Ogmios ChainSync protocol."""

import asyncio
import json
import logging
from typing import Optional, AsyncIterator

from core.blockchain import OgmiosClient

logger = logging.getLogger(__name__)


class BlockIterator:
    """Iterates blocks using Ogmios ChainSync (nextBlock method)."""
    
    def __init__(self, ogmios: OgmiosClient):
        self.ogmios = ogmios
        self._ws = None
    
    async def init_connection(self, start_slot: Optional[int] = None, start_hash: Optional[str] = None):
        """
        Initialize ChainSync connection.
        
        If start_slot/hash provided, finds intersection.
        Otherwise, starts from chain tip.
        """
        if not self.ogmios.is_connected:
            await self.ogmios.connect()
        
        self._ws = self.ogmios._ws
        
        # Get chain tip for intersection
        tip = await self.ogmios.get_chain_tip()
        
        if start_slot and start_hash:
            intersection_point = {"slot": start_slot, "id": start_hash}
        else:
            # Start from tip
            intersection_point = {"slot": tip.slot, "id": tip.block_hash}
        
        # Find intersection
        request = {
            "jsonrpc": "2.0",
            "method": "findIntersection",
            "params": {"points": [intersection_point]},
            "id": self.ogmios._next_request_id(),
        }
        await self._ws.send(json.dumps(request))
        response = json.loads(await self._ws.recv())
        
        if "error" in response or "No intersection found" in str(response):
            logger.warning(f"Could not find intersection, using tip")
            intersection_point = {"slot": tip.slot, "id": tip.block_hash}
            request["params"]["points"][0] = intersection_point
            await self._ws.send(json.dumps(request))
            await self._ws.recv()  # Intersection response
        
        # Request first block (ChainSync protocol)
        await self._request_next_block()
        # Discard the intersection confirmation
        await self._ws.recv()
    
    async def _request_next_block(self):
        """Request next block from ChainSync."""
        request = {
            "jsonrpc": "2.0",
            "method": "nextBlock",
            "id": self.ogmios._next_request_id(),
        }
        await self._ws.send(json.dumps(request))
    
    async def iterate_blocks(self, max_blocks: Optional[int] = None) -> AsyncIterator[dict]:
        """
        Iterate blocks one by one.
        
        Args:
            max_blocks: Maximum number of blocks to process (None = infinite)
        """
        count = 0
        while True:
            if max_blocks and count >= max_blocks:
                break
            
            response_str = await self._ws.recv()
            response = json.loads(response_str)
            
            # Check for rollback
            if "result" in response and response["result"].get("direction") == "backward":
                logger.warning("Rollback detected - stopping iteration")
                break
            
            # Request next block before yielding current
            await self._request_next_block()
            
            if "result" in response and "block" in response["result"]:
                count += 1
                yield response["result"]["block"]
            else:
                logger.warning(f"Unexpected response format: {response}")
