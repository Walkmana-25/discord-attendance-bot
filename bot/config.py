"""Configuration management for the Discord Attendance Bot."""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration settings for the bot."""
    
    # Discord Configuration
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    GUILD_ID: Optional[int] = None
    
    @classmethod
    def _get_guild_id(cls) -> Optional[int]:
        """Get guild ID from environment variable."""
        guild_id = os.getenv("GUILD_ID")
        if guild_id and guild_id.strip() and guild_id.strip().isdigit():
            return int(guild_id.strip())
        return None
    
    # SQLite Database Configuration
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "attendance.db")
    
    # Application Settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration values."""
        missing_vars = []
        
        if not cls.DISCORD_TOKEN:
            missing_vars.append("DISCORD_TOKEN")
            
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    @classmethod
    def setup_logging(cls) -> None:
        """Set up logging configuration."""
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('bot.log')
            ]
        )
