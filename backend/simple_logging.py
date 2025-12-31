"""Simple logging configuration for development."""

import logging
import sys

def setup_simple_logging(level=logging.INFO):
    """Setup simple console logging for development."""
    
    # Create a simple formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Add our console handler
    root_logger.addHandler(console_handler)
    
    # Reduce noise from some loggers
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    
    return root_logger

def get_logger(name):
    """Get a logger with the given name."""
    return logging.getLogger(name)