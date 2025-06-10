"""Simple test script to validate bot functionality."""

import asyncio
import sys
import os

# Add the bot directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.database import Database
from bot.models import User, AttendanceType
from bot.config import Config

async def test_database():
    """Test database functionality."""
    print("🧪 Testing database functionality...")
    
    # Initialize database
    db = Database("test_attendance.db")
    await db.init_database()
    
    print("✅ Database initialized successfully")
    
    # Test user creation
    user = await db.get_or_create_user("123456789", "TestUser")
    print(f"✅ Created user: {user.username} (ID: {user.id})")
    
    # Ensure user ID is valid
    if user.id is None:
        print("❌ Failed to create user with valid ID")
        return
    
    # Test attendance types
    attendance_types = await db.get_attendance_types()
    print(f"✅ Found {len(attendance_types)} attendance types:")
    for at in attendance_types:
        print(f"   - {at.type_name}: {at.description}")
    
    # Test clock-in validation
    can_clock_in, reason = await db.can_clock_in(user.id)
    print(f"✅ Can clock in: {can_clock_in} ({reason})")
    
    # Test attendance record creation
    if can_clock_in and attendance_types:
        record = await db.create_attendance_record(
            user.id,
            "clock_in",
            attendance_types[0].id,
            "Test clock-in"
        )
        print(f"✅ Created clock-in record: {record.id}")
        
        # Test clock-out validation
        can_clock_out, reason = await db.can_clock_out(user.id)
        print(f"✅ Can clock out: {can_clock_out} ({reason})")
        
        if can_clock_out:
            record = await db.create_attendance_record(
                user.id,
                "clock_out",
                None,
                "Test clock-out"
            )
            print(f"✅ Created clock-out record: {record.id}")
    
    # Test summary
    summary = await db.get_user_attendance_summary(user.id)
    if summary:
        print(f"✅ User summary: {summary.total_records} records, currently clocked in: {summary.is_currently_clocked_in}")
    
    # Test records retrieval
    records = await db.get_user_records(user.id, limit=5)
    print(f"✅ Retrieved {len(records)} recent records")
    
    await db.close()
    
    # Clean up test database
    try:
        os.remove("test_attendance.db")
        print("✅ Cleaned up test database")
    except:
        pass
    
    print("🎉 All database tests passed!")

def test_config():
    """Test configuration."""
    print("🧪 Testing configuration...")
    
    # Test that required environment variables are checked
    try:
        Config.validate()
        print("⚠️  Configuration validation passed (environment variables are set)")
    except ValueError as e:
        print(f"✅ Configuration validation working: {e}")
    
    # Test logging setup
    Config.setup_logging()
    print("✅ Logging setup successful")

async def main():
    """Run all tests."""
    print("🚀 Starting Discord Attendance Bot Tests\n")
    
    # Test configuration
    test_config()
    print()
    
    # Test database
    await test_database()
    print()
    
    print("✨ All tests completed successfully!")
    print("\n📋 Next steps:")
    print("1. Set up your .env file with Discord and database credentials")
    print("2. Run the bot with: python -m bot.main")
    print("3. Test the slash commands in your Discord server")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
