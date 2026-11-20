"""
Logging Configuration untuk Trading Command Center
Setup logging dengan format yang konsisten dan rotasi file
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


def setup_logging(
    name: str = "tcc",
    level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    Setup logging untuk Trading Command Center
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Enable file logging
        log_to_console: Enable console logging
        log_dir: Log directory path
        
    Returns:
        Configured logger instance
    """
    
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Log format
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_to_file:
        # Main log file
        main_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / "trading_command_center.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        main_handler.setFormatter(formatter)
        logger.addHandler(main_handler)
        
        # Error log file
        error_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / "error.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
        
        # Daily log files
        daily_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_path / "daily.log",
            when='midnight',
            interval=1,
            backupCount=30
        )
        daily_handler.setFormatter(formatter)
        logger.addHandler(daily_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Get logger instance"""
    if name:
        return logging.getLogger(f"tcc.{name}")
    return logging.getLogger("tcc")


# Create default logger
default_logger = setup_logging()

# Export functions
__all__ = ['setup_logging', 'get_logger', 'default_logger']