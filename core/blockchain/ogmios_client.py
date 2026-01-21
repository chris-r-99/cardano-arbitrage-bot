"""
Ogmios WebSocket client for Cardano blockchain access

Ogmios provides a WebSocket interface to cardano-node, enabling:
- Chain synchronization
- Ledger state queries
- Transaction submission
- Mempool monitoring
"""

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


@dataclass
class ChainTip:
    """Represents the current chain tip"""
    slot: int
    block_hash: str
    block_height: Optional[int] = None


@dataclass
class ProtocolParameters:
    """Subset of protocol parameters useful for transaction building"""
    min_fee_coefficient: int
    min_fee_constant: int
    max_tx_size: int
    # Add more as needed


class OgmiosError(Exception):
    """Base exception for Ogmios errors"""
    pass


class OgmiosConnectionError(OgmiosError):
    """Connection-related errors"""
    pass


class OgmiosQueryError(OgmiosError):
    """Query-related errors"""
    pass


class OgmiosClient:
    """
    Async client for interacting with Ogmios WebSocket API
    
    Supports both Ogmios v5 (JSON-WSP) and v6 (JSON-RPC) protocols.
    """
    
    def __init__(
        self,
        url: str = "ws://localhost:1337",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.url = url
        self.username = username
        self.password = password
        self._ws: Optional[WebSocketClientProtocol] = None
        self._request_id = 0
    
    def _get_headers(self) -> Dict[str, str]:
        """Generate authentication headers if credentials provided"""
        headers = {}
        if self.username and self.password:
            credentials = f"{self.username}:{self.password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        return headers
    
    async def connect(self) -> bool:
        """
        Establish WebSocket connection to Ogmios
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            headers = self._get_headers()
            if headers:
                self._ws = await websockets.connect(
                    self.url,
                    additional_headers=headers,
                )
            else:
                self._ws = await websockets.connect(self.url)
            logger.info(f"Connected to Ogmios at {self.url}")
            return True
        except ConnectionRefusedError:
            logger.error(f"Connection refused. Is Ogmios running at {self.url}?")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Ogmios: {e}")
            return False
    
    async def disconnect(self):
        """Close the WebSocket connection"""
        if self._ws:
            await self._ws.close()
            self._ws = None
            logger.info("Disconnected from Ogmios")
    
    async def __aenter__(self):
        """Async context manager entry"""
        if not await self.connect():
            raise OgmiosConnectionError(f"Failed to connect to {self.url}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    def _next_request_id(self) -> int:
        """Generate next request ID"""
        self._request_id += 1
        return self._request_id
    
    async def _send_request(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Send a request and wait for response
        
        Supports both JSON-WSP (Ogmios v5) and JSON-RPC (Ogmios v6) formats.
        """
        if not self._ws:
            raise OgmiosConnectionError("Not connected to Ogmios")
        
        # Try JSON-RPC format first (Ogmios v6)
        request_id = self._next_request_id()
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id,
        }
        if params:
            request["params"] = params
        
        await self._ws.send(json.dumps(request))
        response_str = await self._ws.recv()
        response = json.loads(response_str)
        
        # Handle JSON-RPC response
        if "result" in response:
            return response["result"]
        elif "error" in response:
            raise OgmiosQueryError(f"Ogmios error: {response['error']}")
        
        # Might be JSON-WSP format, return as-is
        return response
    
    async def get_chain_tip(self) -> ChainTip:
        """
        Query the current chain tip
        
        Returns:
            ChainTip with slot, block hash, and optionally block height
        """
        # Try different method names for compatibility
        methods = [
            "queryLedgerState/tip",  # Ogmios v5
            "queryNetwork/tip",       # Alternative
        ]
        
        for method in methods:
            try:
                result = await self._send_request(method)
                
                # Parse response (format varies by Ogmios version)
                if isinstance(result, dict):
                    slot = result.get("slot", result.get("slotNo", 0))
                    block_hash = result.get("id", result.get("hash", result.get("headerHash", "")))
                    block_height = result.get("height", result.get("blockNo"))
                    
                    return ChainTip(
                        slot=slot,
                        block_hash=block_hash,
                        block_height=block_height,
                    )
            except OgmiosQueryError:
                continue
        
        raise OgmiosQueryError("Failed to query chain tip with any known method")
    
    async def get_current_epoch(self) -> int:
        """Query current epoch number"""
        result = await self._send_request("queryLedgerState/epoch")
        return result if isinstance(result, int) else result.get("epoch", 0)
    
    async def get_protocol_parameters(self) -> Dict[str, Any]:
        """Query current protocol parameters"""
        return await self._send_request("queryLedgerState/protocolParameters")
    
    async def get_utxos_by_address(self, address: str) -> List[Dict[str, Any]]:
        """
        Query UTxOs at a specific address
        
        Args:
            address: Bech32 address to query
            
        Returns:
            List of UTxO dictionaries
        """
        result = await self._send_request(
            "queryLedgerState/utxo",
            {"addresses": [address]}
        )
        return result if isinstance(result, list) else []
    
    async def submit_transaction(self, tx_cbor: str) -> str:
        """
        Submit a signed transaction
        
        Args:
            tx_cbor: Transaction CBOR hex string
            
        Returns:
            Transaction hash if successful
        """
        result = await self._send_request(
            "submitTransaction",
            {"transaction": {"cbor": tx_cbor}}
        )
        return result.get("transaction", {}).get("id", "")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check
        
        Returns:
            Dict with connection status and chain info
        """
        try:
            tip = await self.get_chain_tip()
            return {
                "status": "healthy",
                "connected": True,
                "chain_tip": {
                    "slot": tip.slot,
                    "block_hash": tip.block_hash,
                    "block_height": tip.block_height,
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
            }
