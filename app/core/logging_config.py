
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from app.core.config import settings

def setup_logging():
    """Configures logging for the application."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True) # Ensure log directory exists
    log_file = log_dir / "app.log"

    # Define log format
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Root logger setup (adjust level as needed)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level) # Set root level

    # --- File Handler ---
    # Rotates daily, keeps logs for 30 days
    file_handler = TimedRotatingFileHandler(
        log_file, when="midnight", interval=1, backupCount=30, encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(log_level) # File handler logs at the configured level

    # --- Console Handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    # Console might have a different level, e.g., INFO even if file is DEBUG
    console_handler.setLevel(log_level)

    # Add handlers to the root logger
    # Avoid adding handlers multiple times if setup_logging is called again
    if not root_logger.hasHandlers():
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    else:
        # If handlers exist, maybe update levels or formatters if needed
        # For simplicity now, we assume it's called once at startup
        pass

    # Set levels for libraries that are too verbose
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO) # Keep uvicorn errors
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)


# Call setup function immediately when this module is imported?
# Or call it explicitly in main.py / celery_app.py
# setup_logging() # Let's call it explicitly where needed to ensure settings are loaded

# Example usage (in other modules):
# import logging
# logger = logging.getLogger(__name__)
# logger.info("This is an info message.")
