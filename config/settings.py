"""
Configuration settings - edit values directly here
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """Application settings - configure values below"""
    
    # ===================
    # Ogmios Configuration
    # ===================
    ogmios_url: str = "ws://localhost:1337"
    ogmios_username: Optional[str] = None
    ogmios_password: Optional[str] = None
    
    # ===================
    # Database 
    # ===================
    database_url: Optional[str] = None  # e.g., "postgresql://user:pass@localhost:5432/arbitrage"
    
    # ===================
    # Blockfrost (fallback)
    # ===================
    blockfrost_project_id: Optional[str] = None


# Global settings instance - import this
settings = Settings()
