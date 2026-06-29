from database.connection import DB
from utils.logger import get_logger

logger = get_logger("schema")

def init_db():
    try:
        with DB() as c:

            c.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id SERIAL PRIMARY KEY,
                    phone VARCHAR(20) UNIQUE NOT NULL,
                    full_name VARCHAR(200),
                    service_requested VARCHAR(100),
                    business_name VARCHAR(300),
                    nature_of_business TEXT,
                    registration_type VARCHAR(50),
                    ai_paused BOOLEAN DEFAULT FALSE,
                    within_24h_window BOOLEAN DEFAULT TRUE,
                    last_message_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    phone VARCHAR(20) UNIQUE NOT NULL,
                    fsm_state VARCHAR(100) DEFAULT 'NEW_LEAD',
                    collected_fields JSONB DEFAULT '{}',
                    total_messages INTEGER DEFAULT 0,
                    notified_new BOOLEAN DEFAULT FALSE,
                    notified_qualified BOOLEAN DEFAULT FALSE,
                    followup_count INTEGER DEFAULT 0,
                    last_followup_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (phone) REFERENCES customers(phone) ON DELETE CASCADE
                );
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    phone VARCHAR(20) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    fsm_state VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (phone) REFERENCES customers(phone) ON DELETE CASCADE
                );
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id SERIAL PRIMARY KEY,
                    phone VARCHAR(20),
                    event_type VARCHAR(100) NOT NULL,
                    details JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS followup_log (
                    id SERIAL PRIMARY KEY,
                    phone VARCHAR(20) NOT NULL,
                    message_sent TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

        logger.info("Schema initialized.")
    except Exception as e:
        logger.error(f"Schema init error: {e}")
        raise
