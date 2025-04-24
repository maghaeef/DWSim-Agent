"""
Logging utility module for the Chemical Process Design Agent.
Provides consistent logging throughout the application.
"""

import logging
import os
import sys
from typing import Optional

def setup_logger(level: int = logging.INFO) -> logging.Logger:
    """
    Setup and configure the root logger.
    
    Args:
        level: The logging level (INFO, DEBUG, etc.)
        
    Returns:
        The configured root logger
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    root_logger.addHandler(console_handler)
    
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger with the proper configuration.
    
    Args:
        name: The name for the logger (usually __name__)
        
    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)

def add_file_handler(
    logger: logging.Logger, 
    log_file: str, 
    level: int = logging.INFO
) -> None:
    """
    Add a file handler to an existing logger.
    
    Args:
        logger: The logger to add the handler to
        log_file: Path to the log file
        level: Logging level for the file handler
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)