# Cardano Arbitrage Bot

A modular arbitrage detection and execution bot for Cardano DEXes.

## Project Structure

```
cardano-arbitrage-bot/
├── config/              # Configuration management
│   └── settings.py      # Edit settings directly here
├── core/                # Core modules
│   ├── arbitrage/       # Arbitrage detection & execution (TODO)
│   ├── blockchain/      # Blockchain access (Ogmios client)
│   ├── database/        # Database models & connection (TODO)
│   ├── dex/             # DEX protocol implementations (TODO)
│   └── models/          # Data models
├── main.py              # Entry point / infrastructure test
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Prerequisites

- Python 3.10+
- Running cardano-node (synced)
- Running Ogmios (connected to your node)

## Configuration

Edit `config/settings.py` directly:

```python
@dataclass
class Settings:
    # Ogmios Configuration
    ogmios_url: str = "ws://localhost:1337"  # <-- Change this
    ogmios_username: Optional[str] = None
    ogmios_password: Optional[str] = None
```

## Quick Start

### Option A: Docker (Recommended)

```bash
cd cardano-arbitrage-bot

# 1. Edit config/settings.py with your Ogmios URL

# 2. Build and run
docker-compose build
docker-compose run --rm arbitrage-bot
```

### Option B: Native Python

```bash
cd cardano-arbitrage-bot
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Edit config/settings.py with your Ogmios URL

python main.py
```

### Expected Output

```
============================================================
Cardano Arbitrage Bot - Infrastructure Test
============================================================

Ogmios URL: ws://localhost:1337

[1/3] Testing Ogmios connection...
✅ Connected to Ogmios

[2/3] Querying chain tip...
✅ Chain tip retrieved:
   Slot: 123,456,789
   Block hash: abc123def456...

[3/3] Running health check...
✅ Health check passed

============================================================
✅ All infrastructure tests passed!
============================================================
```

## Development Roadmap

- [x] Step 1: Infrastructure setup (Ogmios connection)
- [ ] Step 2: Fetch pool data from one DEX
- [ ] Step 3: Price calculation
- [ ] Step 4: Multi-DEX price comparison
- [ ] Step 5: Arbitrage detection
- [ ] Step 6: Transaction building
- [ ] Step 7: Execution

## Troubleshooting

### Connection refused

```
❌ FAILED: Could not connect to Ogmios
```

1. Check if cardano-node is running:
   ```bash
   ps aux | grep cardano-node
   ```

2. Check if Ogmios is running:
   ```bash
   ps aux | grep ogmios
   ```

3. Verify the WebSocket URL in `config/settings.py`

### Docker network issues

If running in Docker and Ogmios is on the host:

- **Mac/Windows**: Use `ws://host.docker.internal:1337` in settings.py
- **Linux**: Use `ws://172.17.0.1:1337` or your host's actual IP

For lowest latency on Linux, uncomment `network_mode: host` in docker-compose.yml.

### Chain tip query fails

If connected but chain tip query fails, your Ogmios version might use different method names. Check Ogmios documentation for your version.
