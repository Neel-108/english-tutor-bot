"""
database.py
Database operations for English Tutor Bot
"""

import aiosqlite
from datetime import datetime
from config import DB_PATH, CONTEXT_WINDOW_SIZE, INITIAL_TOKEN_GRANT

# ============================================================================
# INITIALIZATION
# ============================================================================

async def init_db():
    """Initialize database with required tables"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Users table with token_balance
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                grade INTEGER,
                textbook TEXT,
                messagecount INTEGER DEFAULT 0,
                token_balance INTEGER DEFAULT 0,
                tokens_used_today INTEGER DEFAULT 0,
                tokens_used_total INTEGER DEFAULT 0,
                ispaid BOOLEAN DEFAULT 0,
                last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Conversations table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Usage log table - NEVER deleted, permanent audit trail
        await db.execute("""
            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tokens_used INTEGER NOT NULL,
                query_type TEXT NOT NULL,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """)
        
        # Index for fast conversation retrieval
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_timestamp 
            ON conversations(user_id, timestamp DESC)
        """)
        
        # Index for fast usage log queries
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_telegram_date
            ON usage_log(telegram_id, timestamp DESC)
        """)
        
        await db.commit()

# ============================================================================
# USER OPERATIONS
# ============================================================================

async def get_user(telegram_id: int):
    """Get user by telegram_id, returns dict or None"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def create_user(telegram_id: int):
    """Create new user with initial token grant"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (telegram_id, token_balance) VALUES (?, ?)",
            (telegram_id, INITIAL_TOKEN_GRANT)
        )
        await db.commit()

async def update_user_grade(telegram_id: int, grade: int):
    """Update user's grade"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET grade = ? WHERE telegram_id = ?", (grade, telegram_id)
        )
        await db.commit()

async def update_user_textbook(telegram_id: int, textbook: str):
    """Update user's textbook"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET textbook = ? WHERE telegram_id = ?", (textbook, telegram_id)
        )
        await db.commit()

async def get_message_count(telegram_id: int) -> int:
    """Get user's daily message count"""
    user = await get_user(telegram_id)
    return user['messagecount'] if user else 0

async def increment_message_count(telegram_id: int):
    """Increment user's daily message counter"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET messagecount = messagecount + 1 WHERE telegram_id = ?",
            (telegram_id,)
        )
        await db.commit()

async def reset_daily_counters():
    """Reset all users' message counts and daily tokens (cron job at midnight UTC)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET messagecount = 0, tokens_used_today = 0")
        await db.execute("UPDATE users SET last_reset = CURRENT_TIMESTAMP")
        await db.commit()

# ============================================================================
# TOKEN MANAGEMENT
# ============================================================================

async def get_token_balance(telegram_id: int) -> int:
    """Get user's remaining token balance"""
    user = await get_user(telegram_id)
    return user.get('token_balance', 0) if user else 0

async def add_tokens(telegram_id: int, tokens: int):
    """
    Add tokens to user's counters and deduct from balance
    
    Args:
        telegram_id: User's Telegram ID
        tokens: Number of tokens used in this call
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users 
               SET tokens_used_today = tokens_used_today + ?,
                   tokens_used_total = tokens_used_total + ?,
                   token_balance = token_balance - ?
               WHERE telegram_id = ?""",
            (tokens, tokens, tokens, telegram_id)
        )
        await db.commit()

async def deduct_tokens(telegram_id: int, tokens: int, reason: str = "penalty"):
    """
    Deduct tokens from user balance (for penalties)
    
    Args:
        telegram_id: User's Telegram ID
        tokens: Number of tokens to deduct
        reason: Reason for deduction (logged)
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users 
               SET token_balance = token_balance - ?,
                   tokens_used_total = tokens_used_total + ?
               WHERE telegram_id = ?""",
            (tokens, tokens, telegram_id)
        )
        await db.commit()

async def grant_tokens(telegram_id: int, tokens: int):
    """
    Grant tokens to user (admin function)
    
    Args:
        telegram_id: User's Telegram ID
        tokens: Number of tokens to grant
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET token_balance = token_balance + ? WHERE telegram_id = ?",
            (tokens, telegram_id)
        )
        await db.commit()

async def get_token_stats(telegram_id: int) -> dict:
    """
    Get token usage statistics for a user
    
    Returns:
        {
            'tokens_today': int,
            'tokens_total': int,
            'token_balance': int,
            'messages_today': int
        }
    """
    user = await get_user(telegram_id)
    if not user:
        return {
            'tokens_today': 0,
            'tokens_total': 0,
            'token_balance': 0,
            'messages_today': 0
        }
    
    return {
        'tokens_today': user.get('tokens_used_today', 0),
        'tokens_total': user.get('tokens_used_total', 0),
        'token_balance': user.get('token_balance', 0),
        'messages_today': user.get('messagecount', 0)

    }

# ============================================================================
# CONVERSATION OPERATIONS
# ============================================================================

async def save_conversation(telegram_id: int, user_message: str, bot_response: str, tokens_used: int = 0):
    """
    Save conversation pair with token tracking and cleanup old messages
    
    Args:
        telegram_id: User's Telegram ID
        user_message: User's input message
        bot_response: Bot's response
        tokens_used: Tokens consumed in this exchange
    """
    user = await get_user(telegram_id)
    if not user:
        return
    
    user_id = user['user_id']
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Insert new conversation with token tracking
        await db.execute(
            """INSERT INTO conversations (user_id, user_message, bot_response, tokens_used)
               VALUES (?, ?, ?, ?)""",
            (user_id, user_message, bot_response, tokens_used)
        )
        
        # Cleanup: keep only last N messages
        await db.execute(
            """DELETE FROM conversations 
               WHERE user_id = ? 
               AND id NOT IN (
                   SELECT id FROM conversations 
                   WHERE user_id = ? 
                   ORDER BY timestamp DESC 
                   LIMIT ?
               )""",
            (user_id, user_id, CONTEXT_WINDOW_SIZE)
        )
        
        await db.commit()

async def get_recent_conversations(telegram_id: int, limit: int = CONTEXT_WINDOW_SIZE):
    """Get last N conversation pairs for context"""
    user = await get_user(telegram_id)
    if not user:
        return []
    
    user_id = user['user_id']
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT user_message, bot_response 
               FROM conversations 
               WHERE user_id = ? 
               ORDER BY timestamp DESC 
               LIMIT ?""",
            (user_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            # Reverse to get chronological order
            return [(row[0], row[1]) for row in reversed(rows)]

async def delete_user_data(telegram_id: int):
    """
    Reset user profile for /reset command
    
    PRESERVES:
    - tokens_used_total (for billing)
    - tokens_used_today (for billing)
    - token_balance (user keeps their tokens)
    
    CLEARS:
    - grade and textbook (forces re-setup)
    - conversation history
    - message count
    """
    user = await get_user(telegram_id)
    if not user:
        return
    
    user_id = user['user_id']
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Delete conversation history
        await db.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        
        # Reset grade, textbook, and message count BUT preserve token data
        await db.execute(
            """UPDATE users 
               SET grade = NULL, 
                   textbook = NULL, 
                   messagecount = 0 
               WHERE telegram_id = ?""",
            (telegram_id,)
        )
        await db.commit()

# ============================================================================
# PAID STATUS MANAGEMENT
# ============================================================================

async def set_paid_status(telegram_id: int, is_paid: bool):
    """
    Update user's paid subscription status
    
    Args:
        telegram_id: User's Telegram ID
        is_paid: True for paid user, False for free user
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET ispaid = ? WHERE telegram_id = ?",
            (1 if is_paid else 0, telegram_id)
        )
        await db.commit()

async def is_paid_user(telegram_id: int) -> bool:
    """Check if user has paid status"""
    user = await get_user(telegram_id)
    return bool(user['ispaid']) if user else False

# ============================================================================
# USAGE AUDIT LOG - NEVER DELETED
# ============================================================================

async def log_usage(telegram_id: int, tokens_used: int, query_type: str):
    """
    Log usage to permanent audit trail (never deleted)
    
    Args:
        telegram_id: User's Telegram ID
        tokens_used: Tokens consumed in this call
        query_type: 'teaching', 'casual', or 'abuse_penalty'
        
    This log persists even if user deletes conversations or resets profile.
    Used for billing disputes and parental monitoring.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO usage_log (telegram_id, tokens_used, query_type)
               VALUES (?, ?, ?)""",
            (telegram_id, tokens_used, query_type)
        )
        await db.commit()

async def get_usage_report(telegram_id: int, days: int = 7):
    """
    Get usage report for last N days from audit log
    
    Args:
        telegram_id: User's Telegram ID
        days: Number of days to report (default 7)
        
    Returns:
        {
            'daily_breakdown': [...],
            'total_tokens': int,
            'total_messages': int,
            'total_teaching': int,
            'total_casual': int,
            'total_abuse_penalties': int,
            'days': int
        }
    """
    from datetime import datetime, timedelta
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Calculate start date
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Get daily breakdown
        async with db.execute(
            """SELECT 
                DATE(timestamp) as date,
                SUM(tokens_used) as tokens,
                COUNT(*) as messages,
                SUM(CASE WHEN query_type = 'teaching' THEN 1 ELSE 0 END) as teaching_count,
                SUM(CASE WHEN query_type = 'casual' THEN 1 ELSE 0 END) as casual_count,
                SUM(CASE WHEN query_type = 'abuse_penalty' THEN 1 ELSE 0 END) as abuse_count
            FROM usage_log 
            WHERE telegram_id = ? AND DATE(timestamp) >= ?
            GROUP BY DATE(timestamp)
            ORDER BY DATE(timestamp) DESC""",
            (telegram_id, start_date)
        ) as cursor:
            rows = await cursor.fetchall()
            
            daily_breakdown = []
            total_tokens = 0
            total_messages = 0
            total_teaching = 0
            total_casual = 0
            total_abuse = 0
            
            for row in rows:
                row_dict = dict(row)
                daily_breakdown.append(row_dict)
                total_tokens += row_dict['tokens'] or 0
                total_messages += row_dict['messages'] or 0
                total_teaching += row_dict['teaching_count'] or 0
                total_casual += row_dict['casual_count'] or 0
                total_abuse += row_dict['abuse_count'] or 0
            
            return {
                'daily_breakdown': daily_breakdown,
                'total_tokens': total_tokens,
                'total_messages': total_messages,
                'total_teaching': total_teaching,
                'total_casual': total_casual,
                'total_abuse_penalties': total_abuse,
                'days': days
            }

# ============================================================================
# ADMIN FUNCTIONS
# ============================================================================

async def get_all_users():
    """Get all users (admin function)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_user_stats_summary():
    """Get summary stats for all users (admin function)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT 
                COUNT(*) as total_users,
                SUM(tokens_used_total) as total_tokens_consumed,
                SUM(token_balance) as total_tokens_remaining,
                AVG(messagecount) as avg_messages_today
            FROM users
        """) as cursor:
            row = await cursor.fetchone()
            return {
                'total_users': row[0],
                'total_tokens_consumed': row[1] or 0,
                'total_tokens_remaining': row[2] or 0,
                'avg_messages_today': round(row[3] or 0, 1)
            }
