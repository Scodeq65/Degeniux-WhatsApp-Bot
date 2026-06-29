from database.connection import DatabaseContext
from utils.logger import get_logger

logger = get_logger("schema")

def init_db():
    try:
        with DatabaseContext() as cursor:

            # Customers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id SERIAL PRIMARY KEY,
                    phone VARCHAR(20) UNIQUE NOT NULL,
                    full_name VARCHAR(200),
                    email VARCHAR(200),
                    alt_phone VARCHAR(20),
                    service_requested VARCHAR(100),
                    business_name VARCHAR(200),
                    nature_of_business TEXT,
                    registration_type VARCHAR(50),
                    lead_score INTEGER DEFAULT 0,
                    lead_stage VARCHAR(50) DEFAULT 'new_lead',
                    ai_paused BOOLEAN DEFAULT FALSE,
                    human_assigned VARCHAR(100),
                    within_24h_window BOOLEAN DEFAULT TRUE,
                    last_customer_message_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id SERIAL PRIMARY KEY,
                    phone VARCHAR(20) NOT NULL,
                    fsm_state VARCHAR(100) DEFAULT 'NEW_LEAD',
                    collected_fields JSONB DEFAULT '{}',
                    context_summary TEXT,
                    total_messages INTEGER DEFAULT 0,
                    notified_new BOOLEAN DEFAULT FALSE,
                    notified_qualified BOOLEAN DEFAULT FALSE,
                    followup_count INTEGER DEFAULT 0,
                    last_followup_at TIMESTAMP,
                    last_report_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (phone) REFERENCES customers(phone) ON DELETE CASCADE
                );
            """)

            # Messages table
            cursor.execute("""
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

            # Activity log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id SERIAL PRIMARY KEY,
                    phone VARCHAR(20),
                    event_type VARCHAR(100) NOT NULL,
                    details JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Follow-up log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS followup_log (
                    id SERIAL PRIMARY KEY,
                    phone VARCHAR(20) NOT NULL,
                    message_sent TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            logger.info("Database schema initialized successfully.")

    except Exception as e:
        logger.error(f"Schema init error: {e}")
        raise
