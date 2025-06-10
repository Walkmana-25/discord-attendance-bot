"""Utility functions for the Discord Attendance Bot."""

import discord
from datetime import datetime, timezone, timedelta, date
from typing import Optional, Tuple, List, Dict
from .models import AttendanceRecord

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

def get_week_start_end(target_date: datetime, weeks_offset: int = 0) -> Tuple[datetime, datetime]:
    """Get the start (Monday) and end (Sunday) of a week."""
    # Calculate the Monday of the target week
    days_since_monday = target_date.weekday()
    week_start = target_date - timedelta(days=days_since_monday)
    
    # Apply weeks offset
    week_start = week_start + timedelta(weeks=weeks_offset)
    
    # Set to beginning of day
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate week end (Sunday)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    return week_start, week_end

def calculate_work_hours(clock_in: datetime, clock_out: datetime) -> float:
    """Calculate work hours between clock-in and clock-out."""
    if not clock_in or not clock_out:
        return 0.0
    
    duration = clock_out - clock_in
    return duration.total_seconds() / 3600  # Convert to hours

def format_duration(hours: float) -> str:
    """Format duration in hours to human-readable string."""
    if hours == 0:
        return "0時間"
    
    total_minutes = int(hours * 60)
    hours_part = total_minutes // 60
    minutes_part = total_minutes % 60
    
    if minutes_part == 0:
        return f"{hours_part}時間"
    else:
        return f"{hours_part}時間{minutes_part}分"

def group_records_by_date(records: List[AttendanceRecord]) -> Dict[date, List[AttendanceRecord]]:
    """Group attendance records by date."""
    grouped = {}
    
    for record in records:
        if record.timestamp:
            record_date = record.timestamp.date()
            if record_date not in grouped:
                grouped[record_date] = []
            grouped[record_date].append(record)
    
    return grouped

def format_date_japanese(target_date: date) -> str:
    """Format date in Japanese style."""
    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    weekday = weekdays[target_date.weekday()]
    return f"{target_date.month}/{target_date.day}({weekday})"

def calculate_daily_work_hours(day_records: List[AttendanceRecord]) -> Tuple[float, bool]:
    """Calculate work hours for a single day and check for incomplete sessions."""
    total_hours = 0.0
    has_incomplete = False
    
    # Sort records by timestamp
    sorted_records = sorted(day_records, key=lambda r: r.timestamp or datetime.min)
    
    clock_in_time = None
    for record in sorted_records:
        if record.record_type == "clock_in":
            clock_in_time = record.timestamp
        elif record.record_type == "clock_out" and clock_in_time and record.timestamp:
            total_hours += calculate_work_hours(clock_in_time, record.timestamp)
            clock_in_time = None
    
    # Check if there's an incomplete session (clock-in without clock-out)
    if clock_in_time is not None:
        has_incomplete = True
    
    return total_hours, has_incomplete
