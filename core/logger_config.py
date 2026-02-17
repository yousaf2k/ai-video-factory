"""
Logging Configuration Module for AI Video Factory
Provides centralized logging setup with rotating file handlers
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
import config


def _ensure_log_directory():
    """Create logs directory if it doesn't exist"""
    log_dir = getattr(config, 'LOG_DIR', 'logs')
    Path(log_dir).mkdir(exist_ok=True)
    return log_dir


def _get_log_formatter():
    """Get standard log formatter"""
    return logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s():%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def _setup_file_handler(log_file_path, max_bytes, backup_count, level=logging.DEBUG):
    """Create a rotating file handler with specified parameters"""
    handler = RotatingFileHandler(
        log_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    handler.setLevel(level)
    handler.setFormatter(_get_log_formatter())
    return handler


def get_logger(name):
    """
    Get a configured logger with file and console handlers.

    Args:
        name: Logger name (usually module name)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Get config
        log_dir = _ensure_log_directory()
        console_level = getattr(config, 'CONSOLE_LOG_LEVEL', 'INFO')
        file_level = getattr(config, 'FILE_LOG_LEVEL', 'DEBUG')
        max_bytes = getattr(config, 'LOG_MAX_BYTES', 10 * 1024 * 1024)
        backup_count = getattr(config, 'LOG_BACKUP_COUNT', 5)

        # Console handler (INFO and above)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
        console_handler.setFormatter(_get_log_formatter())
        logger.addHandler(console_handler)

        # App log file handler (all levels)
        app_log_path = os.path.join(log_dir, 'app.log')
        app_handler = _setup_file_handler(
            app_log_path, max_bytes, backup_count,
            getattr(logging, file_level.upper(), logging.DEBUG)
        )
        logger.addHandler(app_handler)

        # Error log file handler (ERROR and above)
        error_log_path = os.path.join(log_dir, 'errors.log')
        error_handler = _setup_file_handler(
            error_log_path, max_bytes, backup_count, logging.ERROR
        )
        logger.addHandler(error_handler)

    return logger


def setup_api_logger(name):
    """
    Get a specialized logger for API call tracking.

    Args:
        name: Logger name

    Returns:
        Configured logger for API calls
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Get config
        log_dir = _ensure_log_directory()
        max_bytes = getattr(config, 'LOG_MAX_BYTES', 10 * 1024 * 1024)
        backup_count = getattr(config, 'LOG_BACKUP_COUNT', 5)

        # API calls log file handler
        api_log_path = os.path.join(log_dir, 'api_calls.log')
        api_handler = _setup_file_handler(
            api_log_path, max_bytes, backup_count, logging.DEBUG
        )
        logger.addHandler(api_handler)

        # Also log to console (WARNING and above only)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(_get_log_formatter())
        logger.addHandler(console_handler)

    return logger


def setup_agent_logger(name):
    """
    Get a specialized logger for agent operations.

    Args:
        name: Logger name

    Returns:
        Configured logger for agent operations
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Get config
        log_dir = _ensure_log_directory()
        max_bytes = getattr(config, 'LOG_MAX_BYTES', 10 * 1024 * 1024)
        backup_count = getattr(config, 'LOG_BACKUP_COUNT', 5)

        # Agents log file handler
        agent_log_path = os.path.join(log_dir, 'agents.log')
        agent_handler = _setup_file_handler(
            agent_log_path, max_bytes, backup_count, logging.DEBUG
        )
        logger.addHandler(agent_handler)

        # Also log to console (WARNING and above only)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(_get_log_formatter())
        logger.addHandler(console_handler)

    return logger


def setup_llm_io_logger(name):
    """
    Get a specialized logger for LLM input/output logging.

    Logs full prompts and responses to llm_io.log.

    Args:
        name: Logger name

    Returns:
        Configured logger for LLM I/O
    """
    logger = logging.getLogger(f"llm_io.{name}")

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        log_dir = _ensure_log_directory()
        max_bytes = getattr(config, 'LOG_MAX_BYTES', 10 * 1024 * 1024)
        backup_count = getattr(config, 'LOG_BACKUP_COUNT', 5)

        # LLM I/O log file handler
        llm_io_log_path = os.path.join(log_dir, 'llm_io.log')
        llm_io_handler = _setup_file_handler(
            llm_io_log_path, max_bytes, backup_count, logging.DEBUG
        )
        logger.addHandler(llm_io_handler)

    return logger


if __name__ == "__main__":
    # Test logging configuration
    print("Testing logging configuration...")

    # Test regular logger
    logger = get_logger('test')
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    # Test API logger
    api_logger = setup_api_logger('test_api')
    api_logger.debug("API call test")

    # Test agent logger
    agent_logger = setup_agent_logger('test_agent')
    agent_logger.info("Agent operation test")

    print("\nLogging configuration complete. Check the logs/ directory.")
