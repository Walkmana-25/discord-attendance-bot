"""Slash commands for the Discord Attendance Bot."""

import logging
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List

from .database import Database
from .models import ClockInRequest, ClockOutRequest
from .utils import (
    create_success_embed, 
    create_error_embed, 
    create_info_embed,
    format_attendance_record,
    validate_notes,
    truncate_text
)

logger = logging.getLogger(__name__)

class AttendanceCommands(commands.Cog):
    """Attendance management commands."""

    def __init__(self, bot: commands.Bot, database: Database):
        self.bot = bot
        self.db = database

    async def get_attendance_type_choices(self) -> List[app_commands.Choice[str]]:
        """Get attendance type choices for command parameters."""
        try:
            attendance_types = await self.db.get_attendance_types()
            return [
                app_commands.Choice(name=at.type_name, value=at.type_name)
                for at in attendance_types[:25]  # Discord limit is 25 choices
            ]
        except Exception as e:
            logger.error(f"Error getting attendance types: {e}")
            return [app_commands.Choice(name="Regular Work", value="Regular Work")]

    @app_commands.command(name="clock-in", description="Record your clock-in time")
    @app_commands.describe(
        attendance_type="Type of work you're starting",
        notes="Optional notes about your work session"
    )
    async def clock_in(
        self,
        interaction: discord.Interaction,
        attendance_type: str,
        notes: Optional[str] = None
    ):
        """Handle clock-in command."""
        await interaction.response.defer()
        
        try:
            # Validate and clean notes
            clean_notes = validate_notes(notes)
            
            # Get or create user
            user = await self.db.get_or_create_user(
                str(interaction.user.id),
                interaction.user.display_name
            )
            
            # Check if user can clock in
            if user.id is None:
                embed = create_error_embed("Database Error", "Failed to create user record.", interaction.user)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
                
            can_clock_in, reason = await self.db.can_clock_in(user.id)
            if not can_clock_in:
                embed = create_error_embed("Cannot Clock In", reason, interaction.user)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Get attendance type
            attendance_type_obj = await self.db.get_attendance_type_by_name(attendance_type)
            if not attendance_type_obj:
                embed = create_error_embed(
                    "Invalid Attendance Type",
                    f"Attendance type '{attendance_type}' not found.",
                    interaction.user
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create attendance record
            record = await self.db.create_attendance_record(
                user.id,
                "clock_in",
                attendance_type_obj.id,
                clean_notes
            )
            
            # Create success message
            description = f"Successfully clocked in for **{attendance_type}**"
            if clean_notes:
                description += f"\n📝 Notes: {clean_notes}"
            
            embed = create_success_embed("Clocked In", description, interaction.user)
            await interaction.followup.send(embed=embed)
            
            logger.info(f"User {interaction.user.display_name} clocked in for {attendance_type}")
            
        except Exception as e:
            logger.error(f"Error in clock_in command: {e}")
            embed = create_error_embed(
                "System Error",
                "An error occurred while processing your clock-in. Please try again.",
                interaction.user
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @clock_in.autocomplete('attendance_type')
    async def attendance_type_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Provide autocomplete for attendance types."""
        try:
            attendance_types = await self.db.get_attendance_types()
            choices = []
            
            for at in attendance_types:
                if current.lower() in at.type_name.lower():
                    choices.append(app_commands.Choice(name=at.type_name, value=at.type_name))
                
                if len(choices) >= 25:  # Discord limit
                    break
            
            return choices
        except Exception as e:
            logger.error(f"Error in attendance_type_autocomplete: {e}")
            return [app_commands.Choice(name="Regular Work", value="Regular Work")]

    @app_commands.command(name="clock-out", description="Record your clock-out time")
    @app_commands.describe(notes="Optional notes about your work session")
    async def clock_out(
        self,
        interaction: discord.Interaction,
        notes: Optional[str] = None
    ):
        """Handle clock-out command."""
        await interaction.response.defer()
        
        try:
            # Validate and clean notes
            clean_notes = validate_notes(notes)
            
            # Get or create user
            user = await self.db.get_or_create_user(
                str(interaction.user.id),
                interaction.user.display_name
            )
            
            # Check if user can clock out
            if user.id is None:
                embed = create_error_embed("Database Error", "Failed to create user record.", interaction.user)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
                
            can_clock_out, reason = await self.db.can_clock_out(user.id)
            if not can_clock_out:
                embed = create_error_embed("Cannot Clock Out", reason, interaction.user)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create attendance record
            record = await self.db.create_attendance_record(
                user.id,
                "clock_out",
                None,  # Clock-out doesn't need attendance type
                clean_notes
            )
            
            # Create success message
            description = "Successfully clocked out"
            if clean_notes:
                description += f"\n📝 Notes: {clean_notes}"
            
            embed = create_success_embed("Clocked Out", description, interaction.user)
            await interaction.followup.send(embed=embed)
            
            logger.info(f"User {interaction.user.display_name} clocked out")
            
        except Exception as e:
            logger.error(f"Error in clock_out command: {e}")
            embed = create_error_embed(
                "System Error",
                "An error occurred while processing your clock-out. Please try again.",
                interaction.user
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="my-summary", description="View your attendance summary")
    async def my_summary(self, interaction: discord.Interaction):
        """Show user's attendance summary."""
        await interaction.response.defer()
        
        try:
            # Get or create user
            user = await self.db.get_or_create_user(
                str(interaction.user.id),
                interaction.user.display_name
            )
            
            # Check if user creation was successful
            if user.id is None:
                embed = create_error_embed("Database Error", "Failed to create user record.", interaction.user)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Get attendance summary
            summary = await self.db.get_user_attendance_summary(user.id)
            if not summary:
                embed = create_info_embed(
                    "No Attendance Records",
                    "You haven't recorded any attendance yet. Use `/clock-in` to get started!",
                    interaction.user
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Get recent records
            recent_records = await self.db.get_user_records(user.id, limit=5)
            
            # Create summary embed
            embed = discord.Embed(
                title="📊 Your Attendance Summary",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            # Add summary fields
            embed.add_field(
                name="Total Records",
                value=str(summary.total_records),
                inline=True
            )
            
            status = "🟢 Clocked In" if summary.is_currently_clocked_in else "🔴 Clocked Out"
            embed.add_field(
                name="Current Status",
                value=status,
                inline=True
            )
            
            embed.add_field(name="\u200b", value="\u200b", inline=True)  # Empty field for spacing
            
            # Recent activity
            if recent_records:
                recent_activity = []
                for record in recent_records:
                    # Get attendance type name if it's a clock-in
                    attendance_type_name = None
                    if record.attendance_type_id:
                        try:
                            # This is a simplified approach - in production you might want to cache this
                            attendance_types = await self.db.get_attendance_types()
                            for at in attendance_types:
                                if at.id == record.attendance_type_id:
                                    attendance_type_name = at.type_name
                                    break
                        except Exception:
                            pass
                    
                    formatted_record = format_attendance_record(record, attendance_type_name)
                    recent_activity.append(formatted_record)
                
                activity_text = "\n\n".join(recent_activity)
                embed.add_field(
                    name="Recent Activity",
                    value=truncate_text(activity_text, 1000),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in my_summary command: {e}")
            embed = create_error_embed(
                "System Error",
                "An error occurred while retrieving your summary. Please try again.",
                interaction.user
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot, database: Database):
    """Set up the commands cog."""
    await bot.add_cog(AttendanceCommands(bot, database))
