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
    GUILD_ID: Optional[int] = int(os.getenv("GUILD_ID")) if os.getenv("GUILD_ID") is not None else None
    
    # Database Configuration
    D1_DATABASE_URL: str = os.getenv("D1_DATABASE_URL", "")
    D1_AUTH_TOKEN: str = os.getenv("D1_AUTH_TOKEN", "")
    
    # Application Settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration values."""
        missing_vars = []
        
        if not cls.DISCORD_TOKEN:
            missing_vars.append("DISCORD_TOKEN")
        if not cls.D1_DATABASE_URL:
            missing_vars.append("D1_DATABASE_URL")
        if not cls.D1_AUTH_TOKEN:
            missing_vars.append("D1_AUTH_TOKEN")
            
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
