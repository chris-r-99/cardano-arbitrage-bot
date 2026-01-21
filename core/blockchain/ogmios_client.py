"""Ogmios WebSocket client for Cardano blockchain access."""

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
    slot: int
    block_hash: str
    block_height: Optional[int] = None


class OgmiosError(Exception):
    """Base exception for Ogmios errors."""

class OgmiosConnectionError(OgmiosError):
    """Connection-related errors."""

class OgmiosQueryError(OgmiosError):
    """Query-related errors."""


class OgmiosClient:
    """Async client for Ogmios WebSocket API (v5 and v6)."""
    
    def __init__(self, url: str = "ws://localhost:1337", username: Optional[str] = None, password: Optional[str] = None):
        self.url = url
        self.username = username
        self.password = password
        self._ws: Optional[WebSocketClientProtocol] = None
        self._request_id = 0
    
    def _get_headers(self) -> Dict[str, str]:
        if self.username and self.password:
            encoded = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        return {}
    
    async def connect(self) -> bool:
        """Connect to Ogmios. Returns True on success."""
        try:
            headers = self._get_headers()
            # Increase max_size to handle large UTxO responses (50MB)
            connect_kwargs = {"max_size": 50 * 1024 * 1024}
            if headers:
                connect_kwargs["additional_headers"] = headers
            self._ws = await websockets.connect(self.url, **connect_kwargs)
            logger.info(f"Connected to Ogmios at {self.url}")
            return True
        except ConnectionRefusedError:
            logger.error(f"Connection refused. Is Ogmios running at {self.url}?")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Ogmios: {e}")
            return False
    
    async def disconnect(self):
        if self._ws:
            await self._ws.close()
            self._ws = None
            logger.info("Disconnected from Ogmios")
    
    @property
    def is_connected(self) -> bool:
        return self._ws is not None and self._ws.open
    
    async def __aenter__(self):
        if not await self.connect():
            raise OgmiosConnectionError(f"Failed to connect to {self.url}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id
    
    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None, timeout: float = 30.0) -> Dict[str, Any]:
        """Send JSON-RPC request and wait for response."""
        if not self._ws:
            raise OgmiosConnectionError("Not connected to Ogmios")
        
        request = {"jsonrpc": "2.0", "method": method, "id": self._next_request_id()}
        if params:
            request["params"] = params
        
        try:
            await self._ws.send(json.dumps(request))
            response = json.loads(await asyncio.wait_for(self._ws.recv(), timeout=timeout))
        except asyncio.TimeoutError:
            raise OgmiosQueryError(f"Request timed out after {timeout}s: {method}")
        except Exception as e:
            raise OgmiosQueryError(f"Request failed: {e}")
        
        if "result" in response:
            return response["result"]
        if "error" in response:
            err = response["error"]
            raise OgmiosQueryError(f"Ogmios error: {err.get('message', err) if isinstance(err, dict) else err}")
        return response
    
    async def get_chain_tip(self) -> ChainTip:
        """Query current chain tip."""
        for method in ["queryLedgerState/tip", "queryNetwork/tip"]:
            try:
                r = await self._send_request(method)
                if isinstance(r, dict):
                    return ChainTip(
                        slot=r.get("slot", r.get("slotNo", 0)),
                        block_hash=r.get("id", r.get("hash", r.get("headerHash", ""))),
                        block_height=r.get("height", r.get("blockNo")),
                    )
            except OgmiosQueryError:
                continue
        raise OgmiosQueryError("Failed to query chain tip")
    
    async def get_current_epoch(self) -> int:
        result = await self._send_request("queryLedgerState/epoch")
        return result if isinstance(result, int) else result.get("epoch", 0)
    
    async def get_protocol_parameters(self) -> Dict[str, Any]:
        return await self._send_request("queryLedgerState/protocolParameters")
    
    async def get_utxos_by_address(self, address: str) -> List[Dict[str, Any]]:
        result = await self._send_request("queryLedgerState/utxo", {"addresses": [address]})
        return result if isinstance(result, list) else []
    
    async def get_utxos_by_addresses(self, addresses: List[str]) -> List[Dict[str, Any]]:
        result = await self._send_request("queryLedgerState/utxo", {"addresses": addresses})
        return result if isinstance(result, list) else []
    
    async def get_utxos_by_output_references(self, output_refs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = await self._send_request("queryLedgerState/utxo", {"outputReferences": output_refs})
        return result if isinstance(result, list) else []
    
    async def submit_transaction(self, tx_cbor: str) -> str:
        result = await self._send_request("submitTransaction", {"transaction": {"cbor": tx_cbor}})
        return result.get("transaction", {}).get("id", "")
    
    async def health_check(self) -> Dict[str, Any]:
        try:
            tip = await self.get_chain_tip()
            return {"status": "healthy", "connected": True, "chain_tip": {"slot": tip.slot, "block_hash": tip.block_hash, "block_height": tip.block_height}}
        except Exception as e:
            return {"status": "unhealthy", "connected": False, "error": str(e)}
