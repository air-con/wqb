import logging
import logging.handlers
import os
from pathlib import Path

def setup_logging():
    """
    Set up the global logging configuration for the application.
    """
    # Define the logs directory at the project root
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'wqb_app.log'

    # Create a root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # Set the minimum level for the root logger

    # Prevent logging from propagating to the default handlers
    root_logger.propagate = False

    # Remove any existing handlers to avoid duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Define the log format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create a TimedRotatingFileHandler for log rotation
    # Rotates at midnight, keeps 3 days of logs
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file, when='midnight', interval=1, backupCount=3, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO) # Log INFO and higher to the file

    # Create a StreamHandler to output logs to the console (for development/debugging)
    # This can be configured to a higher level for production
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Add handlers to the root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Configure specific loggers to prevent them from being too verbose if needed
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('celery').setLevel(logging.INFO)

    # Log that the configuration is complete
    logging.info("Logging configured successfully. Logs will be written to %s", log_file)
