# Discord Attendance Bot

A comprehensive Discord bot for tracking employee attendance using slash commands and SQLite database (Cloudflare D1 compatible).

## Features

### Phase 1 (Implemented)
- ✅ `/clock-in` - Record clock-in with attendance type and optional notes
- ✅ `/clock-out` - Record clock-out with optional notes  
- ✅ `/my-summary` - View personal attendance summary and recent activity
- ✅ SQLite database with proper schema and relationships
- ✅ Duplicate clock-in/out prevention
- ✅ Rich Discord embeds with proper formatting
- ✅ Comprehensive error handling and validation
- ✅ Autocomplete for attendance types

### Phase 2 (Future)
- 🔄 `/daily-report` - Administrative daily reports
- 🔄 Advanced reporting and analytics
- 🔄 Export functionality

## Installation

### Prerequisites
- Python 3.9 or higher
- Discord Bot Token
- Cloudflare D1 Database (or SQLite for local development)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/discord-attendance-bot.git
   cd discord-attendance-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   # Discord Bot Configuration
   DISCORD_TOKEN=your_bot_token_here
   GUILD_ID=your_test_guild_id_here

   # Cloudflare D1 Database Configuration  
   D1_DATABASE_URL=your_d1_database_url
   D1_AUTH_TOKEN=your_d1_auth_token

   # Optional Settings
   DEBUG=False
   LOG_LEVEL=INFO
   ```

4. **Run the bot**
   ```bash
   python -m bot.main
   ```

## Database Schema

The bot uses a SQLite-compatible database with the following tables:

### Users
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    discord_id TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Attendance Types
```sql
CREATE TABLE attendance_types (
    id INTEGER PRIMARY KEY,
    type_name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);
```

### Attendance Records
```sql
CREATE TABLE attendance_records (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    record_type TEXT CHECK(record_type IN ('clock_in', 'clock_out')) NOT NULL,
    attendance_type_id INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(attendance_type_id) REFERENCES attendance_types(id)
);
```

## Default Attendance Types

The bot comes pre-configured with these attendance types:
- **Regular Work** - Standard work hours
- **Remote Work** - Working from home
- **Overtime** - Work beyond regular hours  
- **Meeting** - Attending meetings
- **Training** - Training or learning activities

## Usage

### Basic Commands

#### Clock In
```
/clock-in attendance_type:Regular Work notes:Starting my workday
```
- **attendance_type**: Required - Select from available types with autocomplete
- **notes**: Optional - Add notes about your work session (max 500 characters)

#### Clock Out
```
/clock-out notes:Finished for the day
```
- **notes**: Optional - Add notes about your work session (max 500 characters)

#### View Summary
```
/my-summary
```
Shows your personal attendance summary including:
- Total attendance records
- Current status (clocked in/out)
- Recent activity with timestamps

### Business Logic

- **Duplicate Prevention**: Cannot clock-in twice or clock-out without clocking in
- **User Management**: Automatic user registration on first use
- **Validation**: Input validation for notes length and required fields
- **Error Handling**: Comprehensive error messages and logging

## Project Structure

```
discord-attendance-bot/
├── bot/
│   ├── __init__.py
│   ├── main.py           # Bot entry point
│   ├── config.py         # Configuration management
│   ├── database.py       # Database operations
│   ├── models.py         # Pydantic data models
│   ├── commands.py       # Slash command definitions
│   └── utils.py          # Utility functions
├── requirements.txt      # Python dependencies
├── .env.example         # Environment template
├── .gitignore          # Git ignore rules
├── LICENSE             # MIT License
└── README.md           # This file
```

## Development

### Code Quality
- Type hints throughout codebase
- Pydantic models for data validation
- Comprehensive logging
- Async/await for performance
- Proper error handling

### Testing
```bash
# Install development dependencies
pip install pytest pytest-asyncio

# Run tests (when implemented)
pytest
```

## Discord Bot Setup

1. **Create Application**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Click "New Application"
   - Give it a name and create

2. **Create Bot**
   - Go to "Bot" section
   - Click "Add Bot"
   - Copy the token for your `.env` file

3. **Set Permissions**
   - Go to "OAuth2" > "URL Generator"
   - Select "bot" and "applications.commands" scopes
   - Select these bot permissions:
     - Send Messages
     - Use Slash Commands
     - Embed Links
     - Read Message History

4. **Invite Bot**
   - Use the generated URL to invite bot to your server
   - Ensure bot has necessary permissions

## Cloudflare D1 Setup

1. **Create D1 Database**
   ```bash
   wrangler d1 create attendance-bot
   ```

2. **Get Connection Details**
   - Database URL from Cloudflare dashboard
   - API token with D1 permissions

3. **Update Environment**
   - Add D1_DATABASE_URL and D1_AUTH_TOKEN to `.env`

## Troubleshooting

### Common Issues

1. **Bot not responding to slash commands**
   - Ensure bot has "applications.commands" scope
   - Check if commands are synced (check logs)
   - Verify bot permissions in Discord server

2. **Database connection errors**
   - Verify database file permissions (SQLite)
   - Check D1 credentials and API tokens
   - Review database initialization logs

3. **Import errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python version (3.9+ required)

### Logging

The bot creates detailed logs in:
- Console output (configurable level)
- `bot.log` file in project directory

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the logs for error details
