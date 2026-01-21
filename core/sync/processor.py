"""Process blocks to extract orders and pools."""

import logging
from typing import List, Dict, Any
from decimal import Decimal

from core.orders import get_parser_for_script, all_parsers
from core.pools import get_handler, all_handlers
from core.types import Token
from pycardano import Address

logger = logging.getLogger(__name__)

# Known order contract addresses → script hashes
# Minswap V1
ORDER_ADDRESS_TO_SCRIPT = {
    "addr1zxn9efv2f6w82hagxqtn62ju4m293tqvw0uhmdl64ch8uw6j2c79gy9l76sdg0xwhd7r0c0kna0tycz4y5s6mlenh8pq6s3z70": 
        "c620c56751448d1a92184c8f506a4d1f31fc53e55fdd694c8bcda6fa",
}


class BlockProcessor:
    """Processes blocks to extract orders and pools."""
    
    def __init__(self):
        self.order_parsers = {p: p for p in all_parsers()}
        self.pool_handlers = {h: h for h in all_handlers()}
        self.stats = {
            "blocks_processed": 0,
            "orders_found": 0,
            "pools_found": 0,
            "transactions_processed": 0,
        }
    
    def process_block(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single block and extract orders/pools.
        
        Returns:
            Dict with orders, pools, and stats
        """
        slot = block.get("slot", 0)
        height = block.get("height", 0)
        transactions = block.get("transactions", [])
        
        logger.info(f"Processing block {height} (slot {slot}), {len(transactions)} transactions")
        
        orders = []
        pools = []
        
        for tx_idx, tx in enumerate(transactions):
            tx_orders, tx_pools = self._process_transaction(block, tx_idx, tx)
            orders.extend(tx_orders)
            pools.extend(tx_pools)
            self.stats["transactions_processed"] += 1
        
        self.stats["blocks_processed"] += 1
        self.stats["orders_found"] += len(orders)
        self.stats["pools_found"] += len(pools)
        
        return {
            "block": {"slot": slot, "height": height, "hash": block.get("id", "")},
            "orders": orders,
            "pools": pools,
            "stats": self.stats.copy(),
        }
    
    def _process_transaction(self, block: Dict, tx_idx: int, tx: Dict) -> tuple[List, List]:
        """Process a single transaction."""
        orders = []
        pools = []
        
        # Check outputs for orders/pools
        for output_idx, output in enumerate(tx.get("outputs", [])):
            address = output.get("address", "")
            value = output.get("value", {})
            datum_cbor_hex = output.get("datum")
            
            if not datum_cbor_hex:
                continue
            
            utxo_id = f"{tx['id']}#{output_idx}"
            utxo = {
                "tx_hash": tx["id"],
                "output_index": output_idx,
                "address": address,
                "value": value,
                "datum_cbor": datum_cbor_hex,
            }
            
            # Extract script hash from address for order detection
            # Check known order addresses first
            if address in ORDER_ADDRESS_TO_SCRIPT:
                utxo["script_hash"] = ORDER_ADDRESS_TO_SCRIPT[address]
            else:
                # Try to extract from address
                try:
                    addr = Address.decode(address)
                    # For script addresses, payment_part is ScriptHash
                    if hasattr(addr.payment_part, 'payload'):
                        script_hash = addr.payment_part.payload.hex()
                        utxo["script_hash"] = script_hash
                except Exception:
                    pass  # Not a script address or decode failed
            
            # Try to parse as order
            for parser in self.order_parsers.values():
                if parser.is_order_utxo(utxo):
                    try:
                        datum_cbor = bytes.fromhex(datum_cbor_hex)
                        order = parser.parse_order(utxo, datum_cbor, utxo_id)
                        if order:
                            orders.append({
                                "utxo_id": utxo_id,
                                "order_type": order.order_type,
                                "bid_token": order.bid_token.to_hex() if hasattr(order.bid_token, 'to_hex') else str(order.bid_token),
                                "ask_token": order.ask_token.to_hex() if hasattr(order.ask_token, 'to_hex') else str(order.ask_token),
                                "bid_amount": order.bid_amount,
                                "ask_amount": order.ask_amount,
                            })
                            break  # Found order, don't try other parsers
                    except Exception as e:
                        logger.debug(f"Failed to parse order {utxo_id}: {e}")
                    break  # Tried this parser, move on
            
            # Try to parse as pool (check for NFT)
            for handler in self.pool_handlers.values():
                if handler.is_pool_utxo(utxo):
                    try:
                        datum_cbor = bytes.fromhex(datum_cbor_hex)
                        pool = handler.parse_pool(utxo, datum_cbor, utxo_id)
                        if pool:
                            pools.append({
                                "utxo_id": utxo_id,
                                "pool_type": pool.pool_type,
                                "token_a": pool.token_a.to_hex() if hasattr(pool.token_a, 'to_hex') else str(pool.token_a),
                                "token_b": pool.token_b.to_hex() if hasattr(pool.token_b, 'to_hex') else str(pool.token_b),
                                "reserve_a": pool.reserve_a,
                                "reserve_b": pool.reserve_b,
                            })
                            break  # Found pool, don't try other handlers
                    except Exception as e:
                        logger.debug(f"Failed to parse pool {utxo_id}: {e}")
                    break
        
        return orders, pools
