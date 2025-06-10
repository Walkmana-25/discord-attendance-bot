"""Data models for the Discord Attendance Bot."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    """User model representing a Discord user."""
    id: Optional[int] = None
    discord_id: str = Field(..., description="Discord user ID")
    username: str = Field(..., description="Discord username")
    created_at: Optional[datetime] = None


class AttendanceType(BaseModel):
    """Attendance type model for categorizing different types of work."""
    id: Optional[int] = None
    type_name: str = Field(..., description="Name of the attendance type")
    description: Optional[str] = Field(None, description="Description of the attendance type")
    is_active: bool = Field(True, description="Whether this attendance type is active")


class AttendanceRecord(BaseModel):
    """Attendance record model for tracking clock-in/clock-out events."""
    id: Optional[int] = None
    user_id: int = Field(..., description="User ID from users table")
    record_type: str = Field(..., description="Type of record: clock_in or clock_out")
    attendance_type_id: Optional[int] = Field(None, description="Attendance type ID")
    timestamp: Optional[datetime] = None
    notes: Optional[str] = Field(None, description="Optional notes for the record")

    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class ClockInRequest(BaseModel):
    """Request model for clock-in command."""
    attendance_type: str = Field(..., description="Type of attendance")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")


class ClockOutRequest(BaseModel):
    """Request model for clock-out command."""
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")


class AttendanceSummary(BaseModel):
    """Summary model for attendance reports."""
    user_id: int
    username: str
    total_records: int
    latest_clock_in: Optional[datetime] = None
    latest_clock_out: Optional[datetime] = None
    is_currently_clocked_in: bool = False
