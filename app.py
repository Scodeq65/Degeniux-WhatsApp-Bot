from flask import Flask
import atexit
from config.settings import Config
from database.connection import init_pool
from database.schema import init_db
from routes.webhook import webhook_bp
from routes.admin import admin_bp
from routes.control import control_bp
from routes.conversation import conversation_bp
from utils.logger import get_logger

logger = get_logger("app")


def create_app():
    app = Flask(__name__)
    app.secret_key = Config.FLASK_SECRET_KEY

    # Initialize database
    init_pool()
    init_db()

    # Register blueprints
    app.register_blueprint(webhook_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(control_bp)
    app.register_blueprint(conversation_bp)

    # Home route
    @app.route("/", methods=["GET"])
    def home():
        return "Degenius WhatsApp AI Agent is running! ✅", 200

    # Health check
    @app.route("/health", methods=["GET"])
    def health():
        return {"status": "healthy", "service": "Degenius WhatsApp Bot"}, 200

    # Start scheduler
    _start_scheduler()

    logger.info("Degenius WhatsApp AI Agent started successfully.")
    return app


def _start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from scheduler.jobs import run_followups, run_daily_report

        scheduler = BackgroundScheduler(timezone="Africa/Lagos")
        scheduler.add_job(run_followups, 'interval', hours=1, id='followup_job')
        scheduler.add_job(
            run_daily_report,
            'cron',
            hour=Config.REPORT_HOUR,
            minute=0,
            id='report_job'
        )
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown(wait=False))
        logger.info("Scheduler started — follow-ups every hour, report at 7AM WAT")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")


app = create_app()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
