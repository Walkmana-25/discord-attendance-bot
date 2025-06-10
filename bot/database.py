"""Database operations for the Discord Attendance Bot."""

import logging
import aiosqlite
from datetime import datetime
from typing import List, Optional, Tuple
from .models import User, AttendanceType, AttendanceRecord, AttendanceSummary
from .config import Config

logger = logging.getLogger(__name__)

class Database:
    """Database operations handler for attendance tracking."""

    def __init__(self, db_path: str = "attendance.db"):
        """Initialize database connection."""
        self.db_path = db_path

    async def init_database(self) -> None:
        """Initialize database tables and default data."""
        async with aiosqlite.connect(self.db_path) as db:
            # Enable foreign key constraints
            await db.execute("PRAGMA foreign_keys = ON")
            
            # Create users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    discord_id TEXT UNIQUE NOT NULL,
                    username TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create attendance_types table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS attendance_types (
                    id INTEGER PRIMARY KEY,
                    type_name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Create attendance_records table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS attendance_records (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    record_type TEXT CHECK(record_type IN ('clock_in', 'clock_out')) NOT NULL,
                    attendance_type_id INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(attendance_type_id) REFERENCES attendance_types(id)
                )
            """)
            
            # Create indexes for better performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_attendance_records_user_id ON attendance_records(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_attendance_records_timestamp ON attendance_records(timestamp)")
            
            await db.commit()
            
            # Insert default attendance types
            await self._insert_default_attendance_types()
            
        logger.info("Database initialized successfully")

    async def _insert_default_attendance_types(self) -> None:
        """Insert default attendance types if they don't exist."""
        default_types = [
            ("Regular Work", "Standard work hours"),
            ("Remote Work", "Working from home"),
            ("Overtime", "Work beyond regular hours"),
            ("Meeting", "Attending meetings"),
            ("Training", "Training or learning activities"),
        ]
        
        async with aiosqlite.connect(self.db_path) as db:
            for type_name, description in default_types:
                await db.execute("""
                    INSERT OR IGNORE INTO attendance_types (type_name, description)
                    VALUES (?, ?)
                """, (type_name, description))
            await db.commit()

    async def get_or_create_user(self, discord_id: str, username: str) -> User:
        """Get existing user or create new one."""
        async with aiosqlite.connect(self.db_path) as db:
            # Try to get existing user
            cursor = await db.execute(
                "SELECT id, discord_id, username, created_at FROM users WHERE discord_id = ?",
                (discord_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                return User(
                    id=row[0],
                    discord_id=row[1],
                    username=row[2],
                    created_at=datetime.fromisoformat(row[3]) if row[3] else None
                )
            
            # Create new user
            cursor = await db.execute(
                "INSERT INTO users (discord_id, username) VALUES (?, ?)",
                (discord_id, username)
            )
            await db.commit()
            
            user_id = cursor.lastrowid
            logger.info(f"Created new user: {username} (ID: {user_id})")
            
            return User(
                id=user_id,
                discord_id=discord_id,
                username=username,
                created_at=datetime.now()
            )

    async def get_attendance_types(self) -> List[AttendanceType]:
        """Get all active attendance types."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, type_name, description, is_active FROM attendance_types WHERE is_active = TRUE"
            )
            rows = await cursor.fetchall()
            
            return [
                AttendanceType(
                    id=row[0],
                    type_name=row[1],
                    description=row[2],
                    is_active=bool(row[3])
                )
                for row in rows
            ]

    async def get_attendance_type_by_name(self, type_name: str) -> Optional[AttendanceType]:
        """Get attendance type by name."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, type_name, description, is_active FROM attendance_types WHERE type_name = ? AND is_active = TRUE",
                (type_name,)
            )
            row = await cursor.fetchone()
            
            if row:
                return AttendanceType(
                    id=row[0],
                    type_name=row[1],
                    description=row[2],
                    is_active=bool(row[3])
                )
            return None

    async def get_latest_record(self, user_id: int) -> Optional[AttendanceRecord]:
        """Get the latest attendance record for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, user_id, record_type, attendance_type_id, timestamp, notes
                FROM attendance_records
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (user_id,))
            row = await cursor.fetchone()
            
            if row:
                return AttendanceRecord(
                    id=row[0],
                    user_id=row[1],
                    record_type=row[2],
                    attendance_type_id=row[3],
                    timestamp=datetime.fromisoformat(row[4]) if row[4] else None,
                    notes=row[5]
                )
            return None

    async def can_clock_in(self, user_id: int) -> Tuple[bool, str]:
        """Check if user can clock in (not already clocked in)."""
        latest_record = await self.get_latest_record(user_id)
        
        if latest_record is None:
            return True, "No previous records found"
        
        if latest_record.record_type == "clock_out":
            return True, "Last record was clock-out"
        
        return False, "Already clocked in. Please clock out first."

    async def can_clock_out(self, user_id: int) -> Tuple[bool, str]:
        """Check if user can clock out (currently clocked in)."""
        latest_record = await self.get_latest_record(user_id)
        
        if latest_record is None:
            return False, "No clock-in record found. Please clock in first."
        
        if latest_record.record_type == "clock_in":
            return True, "Currently clocked in"
        
        return False, "Not currently clocked in. Please clock in first."

    async def create_attendance_record(
        self,
        user_id: int,
        record_type: str,
        attendance_type_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> AttendanceRecord:
        """Create a new attendance record."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO attendance_records (user_id, record_type, attendance_type_id, notes)
                VALUES (?, ?, ?, ?)
            """, (user_id, record_type, attendance_type_id, notes))
            await db.commit()
            
            record_id = cursor.lastrowid
            
            # Get the created record with timestamp
            cursor = await db.execute("""
                SELECT id, user_id, record_type, attendance_type_id, timestamp, notes
                FROM attendance_records
                WHERE id = ?
            """, (record_id,))
            row = await cursor.fetchone()
            
            record = AttendanceRecord(
                id=row[0],
                user_id=row[1],
                record_type=row[2],
                attendance_type_id=row[3],
                timestamp=datetime.fromisoformat(row[4]) if row[4] else None,
                notes=row[5]
            )
            
            logger.info(f"Created {record_type} record for user {user_id}")
            return record

    async def get_user_attendance_summary(self, user_id: int) -> Optional[AttendanceSummary]:
        """Get attendance summary for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            # Get user info and record count
            cursor = await db.execute("""
                SELECT u.username, COUNT(ar.id) as total_records
                FROM users u
                LEFT JOIN attendance_records ar ON u.id = ar.user_id
                WHERE u.id = ?
                GROUP BY u.id, u.username
            """, (user_id,))
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            username, total_records = row
            
            # Get latest clock-in and clock-out times
            cursor = await db.execute("""
                SELECT record_type, MAX(timestamp) as latest_time
                FROM attendance_records
                WHERE user_id = ?
                GROUP BY record_type
            """, (user_id,))
            
            latest_times = {row[0]: datetime.fromisoformat(row[1]) for row in await cursor.fetchall()}
            
            # Check if currently clocked in
            latest_record = await self.get_latest_record(user_id)
            is_currently_clocked_in = bool(latest_record and latest_record.record_type == "clock_in")
            
            return AttendanceSummary(
                user_id=user_id,
                username=username,
                total_records=total_records,
                latest_clock_in=latest_times.get("clock_in"),
                latest_clock_out=latest_times.get("clock_out"),
                is_currently_clocked_in=is_currently_clocked_in
            )

    async def get_user_records(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> List[AttendanceRecord]:
        """Get attendance records for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, user_id, record_type, attendance_type_id, timestamp, notes
                FROM attendance_records
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset))
            
            rows = await cursor.fetchall()
            
            return [
                AttendanceRecord(
                    id=row[0],
                    user_id=row[1],
                    record_type=row[2],
                    attendance_type_id=row[3],
                    timestamp=datetime.fromisoformat(row[4]) if row[4] else None,
                    notes=row[5]
                )
                for row in rows
            ]

    async def close(self) -> None:
        """Close database connections."""
        # aiosqlite handles connection closing automatically
        pass
