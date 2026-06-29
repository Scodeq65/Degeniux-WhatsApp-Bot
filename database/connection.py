from psycopg2 import pool
from config.settings import Config
from utils.logger import get_logger

logger = get_logger("database")

_pool = None

def init_pool():
    global _pool
    try:
        _pool = pool.ThreadedConnectionPool(
            Config.DB_POOL_MIN,
            Config.DB_POOL_MAX,
            Config.DATABASE_URL
        )
        logger.info("Database pool initialized.")
    except Exception as e:
        logger.error(f"Pool init error: {e}")
        raise

def get_connection():
    global _pool
    if _pool is None:
        init_pool()
    return _pool.getconn()

def release_connection(conn):
    global _pool
    if _pool and conn:
        _pool.putconn(conn)

class DB:
    """Context manager for safe database transactions."""
    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            if self.conn:
                self.conn.rollback()
            logger.error(f"DB rollback: {exc_val}")
        else:
            if self.conn:
                self.conn.commit()
        if self.cursor:
            self.cursor.close()
        release_connection(self.conn)
        return False
