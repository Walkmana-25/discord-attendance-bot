"""Main entry point for the Discord Attendance Bot."""

import asyncio
import logging
import signal
import sys
from typing import Optional

import discord
from discord.ext import commands

from .config import Config
from .database import Database
from .commands import setup as setup_commands

logger = logging.getLogger(__name__)

class AttendanceBot(commands.Bot):
    """Discord Attendance Bot main class."""
    
    def __init__(self):
        """Initialize the bot."""
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        
        # Initialize bot
        super().__init__(
            command_prefix='!',  # We'll primarily use slash commands
            intents=intents,
            help_command=None
        )
        
        # Initialize database
        self.database: Optional[Database] = None
        
    async def setup_hook(self) -> None:
        """Set up the bot after login."""
        logger.info("Setting up bot...")
        
        # Initialize database
        self.database = Database()
        await self.database.init_database()
        
        # Set up commands
        await setup_commands(self, self.database)
        
        # Sync commands (for development - in production you'd do this manually)
        if Config.GUILD_ID:
            guild = discord.Object(id=Config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands to guild {Config.GUILD_ID}")
        else:
            await self.tree.sync()
            logger.info("Synced commands globally")
        
        logger.info("Bot setup complete!")
    
    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Discord.py version: {discord.__version__}")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="for /clock-in and /clock-out"
        )
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error) -> None:
        """Handle command errors."""
        logger.error(f"Command error: {error}")
        
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
        
        # Send error message to user
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while processing your command.",
            color=discord.Color.red()
        )
        
        try:
            await ctx.send(embed=embed, ephemeral=True)
        except:
            pass
    
    async def on_app_command_error(self, interaction: discord.Interaction, error) -> None:
        """Handle application command errors."""
        logger.error(f"App command error: {error}")
        
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while processing your command.",
            color=discord.Color.red()
        )
        
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass
    
    async def close(self) -> None:
        """Clean up when bot is shutting down."""
        logger.info("Shutting down bot...")
        
        if self.database:
            await self.database.close()
        
        await super().close()

async def main():
    """Main function to run the bot."""
    # Set up configuration and logging
    try:
        Config.validate()
        Config.setup_logging()
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    
    logger.info("Starting Discord Attendance Bot...")
    
    # Create and run bot
    bot = AttendanceBot()
    
    async def shutdown_handler():
        """Handle shutdown gracefully."""
        logger.info("Received shutdown signal, closing bot...")
        await bot.close()
    
    # Set up signal handlers for graceful shutdown
    if sys.platform != 'win32':
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown_handler()))
    
    try:
        await bot.start(Config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    # Handle Windows compatibility
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
