"""Utility functions for the Discord Attendance Bot."""

import discord
from datetime import datetime, timezone
from typing import Optional

def format_timestamp(dt: datetime, style: str = "f") -> str:
    """Format datetime as Discord timestamp."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    timestamp = int(dt.timestamp())
    return f"<t:{timestamp}:{style}>"

def create_success_embed(title: str, description: str, user: discord.User) -> discord.Embed:
    """Create a success embed message."""
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
    return embed

def create_error_embed(title: str, description: str, user: Optional[discord.User] = None) -> discord.Embed:
    """Create an error embed message."""
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc)
    )
    if user:
        embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
    return embed

def create_info_embed(title: str, description: str, user: Optional[discord.User] = None) -> discord.Embed:
    """Create an info embed message."""
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    if user:
        embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else None)
    return embed

def format_attendance_record(record, attendance_type_name: Optional[str] = None) -> str:
    """Format an attendance record for display."""
    record_type_display = "🟢 Clock In" if record.record_type == "clock_in" else "🔴 Clock Out"
    timestamp = format_timestamp(record.timestamp) if record.timestamp else "Unknown time"
    
    formatted = f"{record_type_display} - {timestamp}"
    
    if attendance_type_name and record.record_type == "clock_in":
        formatted += f" ({attendance_type_name})"
    
    if record.notes:
        formatted += f"\n📝 {record.notes}"
    
    return formatted

def truncate_text(text: str, max_length: int = 1000) -> str:
    """Truncate text to fit within Discord limits."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def validate_notes(notes: Optional[str]) -> Optional[str]:
    """Validate and clean notes input."""
    if not notes:
        return None
    
    # Remove extra whitespace
    cleaned = notes.strip()
    
    # Check length
    if len(cleaned) > 500:
        return cleaned[:500]
    
    return cleaned if cleaned else None
