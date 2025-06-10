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
    truncate_text,
    get_week_start_end,
    group_records_by_date,
    format_date_japanese,
    calculate_daily_work_hours,
    format_duration
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

    @app_commands.command(name="add-attendance-type", description="Add a new attendance type")
    @app_commands.describe(
        type_name="Name of the new attendance type",
        description="Optional description for the attendance type"
    )
    async def add_attendance_type(
        self,
        interaction: discord.Interaction,
        type_name: str,
        description: Optional[str] = None
    ):
        """Add a new attendance type."""
        await interaction.response.defer()
        
        try:
            # Validate type_name
            if not type_name or len(type_name.strip()) == 0:
                embed = create_error_embed(
                    "Invalid Input",
                    "Attendance type name cannot be empty.",
                    interaction.user
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Clean and validate inputs
            clean_type_name = type_name.strip()
            clean_description = description.strip() if description else ""
            
            # Check length limits
            if len(clean_type_name) > 50:
                embed = create_error_embed(
                    "Invalid Input",
                    "Attendance type name must be 50 characters or less.",
                    interaction.user
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if len(clean_description) > 200:
                embed = create_error_embed(
                    "Invalid Input",
                    "Description must be 200 characters or less.",
                    interaction.user
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Check if attendance type already exists
            if await self.db.attendance_type_exists(clean_type_name):
                embed = create_error_embed(
                    "Duplicate Entry",
                    f"Attendance type '{clean_type_name}' already exists.",
                    interaction.user
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create new attendance type
            new_type = await self.db.create_attendance_type(clean_type_name, clean_description)
            
            # Create success message
            description_text = f"Successfully added attendance type **{new_type.type_name}**"
            if new_type.description:
                description_text += f"\n📝 Description: {new_type.description}"
            
            embed = create_success_embed("Attendance Type Added", description_text, interaction.user)
            await interaction.followup.send(embed=embed)
            
            logger.info(f"User {interaction.user.display_name} added attendance type: {new_type.type_name}")
            
        except Exception as e:
            logger.error(f"Error in add_attendance_type command: {e}")
            embed = create_error_embed(
                "System Error",
                "An error occurred while adding the attendance type. Please try again.",
                interaction.user
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="list-attendance-types", description="List all attendance types")
    async def list_attendance_types(self, interaction: discord.Interaction):
        """List all attendance types."""
        await interaction.response.defer()
        
        try:
            # Get all attendance types
            all_types = await self.db.get_all_attendance_types()
            
            if not all_types:
                embed = create_info_embed(
                    "No Attendance Types",
                    "No attendance types found in the system.",
                    interaction.user
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Separate active and inactive types
            active_types = [at for at in all_types if at.is_active]
            inactive_types = [at for at in all_types if not at.is_active]
            
            # Create embed
            embed = discord.Embed(
                title="📋 Attendance Types",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            # Add active types
            if active_types:
                active_list = []
                for at in active_types:
                    type_text = f"**{at.type_name}**"
                    if at.description:
                        type_text += f"\n  ├ {at.description}"
                    active_list.append(type_text)
                
                embed.add_field(
                    name="🟢 Active Types",
                    value="\n\n".join(active_list),
                    inline=False
                )
            
            # Add inactive types if any
            if inactive_types:
                inactive_list = []
                for at in inactive_types:
                    type_text = f"~~{at.type_name}~~"
                    if at.description:
                        type_text += f"\n  ├ ~~{at.description}~~"
                    inactive_list.append(type_text)
                
                embed.add_field(
                    name="🔴 Inactive Types",
                    value="\n\n".join(inactive_list),
                    inline=False
                )
            
            # Add footer with count
            total_count = len(all_types)
            active_count = len(active_types)
            embed.set_footer(text=f"Total: {total_count} types ({active_count} active)")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in list_attendance_types command: {e}")
            embed = create_error_embed(
                "System Error",
                "An error occurred while retrieving attendance types. Please try again.",
                interaction.user
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="this-week", description="View your attendance for this week")
    async def this_week(self, interaction: discord.Interaction):
        """Show user's attendance for the current week."""
        await interaction.response.defer()
        
        try:
            await self._show_weekly_attendance(interaction, weeks_offset=0, week_name="今週")
        except Exception as e:
            logger.error(f"Error in this_week command: {e}")
            embed = create_error_embed(
                "System Error",
                "An error occurred while retrieving this week's attendance. Please try again.",
                interaction.user
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="last-week", description="View your attendance for last week")
    async def last_week(self, interaction: discord.Interaction):
        """Show user's attendance for the previous week."""
        await interaction.response.defer()
        
        try:
            await self._show_weekly_attendance(interaction, weeks_offset=-1, week_name="先週")
        except Exception as e:
            logger.error(f"Error in last_week command: {e}")
            embed = create_error_embed(
                "System Error",
                "An error occurred while retrieving last week's attendance. Please try again.",
                interaction.user
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    async def _show_weekly_attendance(self, interaction: discord.Interaction, weeks_offset: int, week_name: str):
        """Helper method to show weekly attendance."""
        from datetime import datetime, timedelta
        
        # Get or create user
        user = await self.db.get_or_create_user(
            str(interaction.user.id),
            interaction.user.display_name
        )
        
        if user.id is None:
            embed = create_error_embed("Database Error", "Failed to create user record.", interaction.user)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Calculate week start and end
        now = datetime.now()
        week_start, week_end = get_week_start_end(now, weeks_offset)
        
        # Get records for the week
        records = await self.db.get_user_records_by_week(user.id, week_start, week_end)
        
        if not records:
            embed = create_info_embed(
                f"{week_name}の履歴",
                f"{week_name}の出勤記録がありません。",
                interaction.user
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Group records by date
        grouped_records = group_records_by_date(records)
        
        # Get attendance types for display
        attendance_types = await self.db.get_attendance_types()
        type_map = {at.id: at.type_name for at in attendance_types}
        
        # Create embed
        embed = discord.Embed(
            title=f"📅 {week_name}の履歴",
            description=f"{week_start.strftime('%Y年%m月%d日')} ～ {week_end.strftime('%Y年%m月%d日')}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        
        # Process each day
        total_work_hours = 0.0
        work_days = 0
        incomplete_sessions = []
        attendance_type_count = {}
        
        for current_date in [week_start.date() + timedelta(days=i) for i in range(7)]:
            day_records = grouped_records.get(current_date, [])
            
            if day_records:
                work_days += 1
                day_hours, has_incomplete = calculate_daily_work_hours(day_records)
                total_work_hours += day_hours
                
                if has_incomplete:
                    incomplete_sessions.append(current_date)
                
                # Count attendance types
                for record in day_records:
                    if record.record_type == "clock_in" and record.attendance_type_id:
                        type_name = type_map.get(record.attendance_type_id, "Unknown")
                        attendance_type_count[type_name] = attendance_type_count.get(type_name, 0) + 1
                
                # Format daily summary
                day_text = []
                sorted_day_records = sorted(day_records, key=lambda r: r.timestamp or datetime.min)
                
                for record in sorted_day_records:
                    if record.timestamp:
                        time_str = record.timestamp.strftime('%H:%M')
                        if record.record_type == "clock_in":
                            type_name = type_map.get(record.attendance_type_id, "")
                            day_text.append(f"🟢 {time_str} 出勤 ({type_name})")
                        else:
                            day_text.append(f"🔴 {time_str} 退勤")
                
                if day_hours > 0:
                    day_text.append(f"⏰ 勤務時間: {format_duration(day_hours)}")
                
                if has_incomplete:
                    day_text.append("⚠️ 未完了セッション")
                
                embed.add_field(
                    name=format_date_japanese(current_date),
                    value="\n".join(day_text) if day_text else "記録なし",
                    inline=False
                )
        
        # Add weekly summary
        summary_parts = []
        summary_parts.append(f"📊 **週間統計**")
        summary_parts.append(f"総勤務時間: {format_duration(total_work_hours)}")
        summary_parts.append(f"出勤日数: {work_days}日")
        
        if work_days > 0:
            avg_hours = total_work_hours / work_days
            summary_parts.append(f"平均勤務時間: {format_duration(avg_hours)}")
        
        if attendance_type_count:
            most_used = max(attendance_type_count.items(), key=lambda x: x[1])
            summary_parts.append(f"主な勤務タイプ: {most_used[0]} ({most_used[1]}回)")
        
        if incomplete_sessions:
            summary_parts.append(f"⚠️ 未完了セッション: {len(incomplete_sessions)}日")
        
        embed.add_field(
            name="",
            value="\n".join(summary_parts),
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot, database: Database):
    """Set up the commands cog."""
    await bot.add_cog(AttendanceCommands(bot, database))
