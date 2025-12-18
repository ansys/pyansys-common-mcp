"""Unit tests for logging_config module."""

import logging
import os
import tempfile
from pathlib import Path

import pytest

from ansys.common.mcp.logging_config import get_logger, setup_logging


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_default(self):
        """Test setup_logging with default parameters."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        logger = setup_logging()
        
        assert logger is not None
        assert len(logger.handlers) > 0
        assert logger.level == logging.INFO
        
    def test_setup_logging_debug_level(self):
        """Test setup_logging with DEBUG level."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        logger = setup_logging(level="DEBUG")
        
        assert logger.level == logging.DEBUG
        
    def test_setup_logging_error_level(self):
        """Test setup_logging with ERROR level."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        logger = setup_logging(level="ERROR")
        
        assert logger.level == logging.ERROR
        
    def test_setup_logging_with_file(self):
        """Test setup_logging with file output."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = setup_logging(log_file=str(log_file))
            
            # Should have stderr and file handlers
            assert len(logger.handlers) >= 2
            
            # Write a log message
            logger.info("Test message")
            
            # Check that file exists and contains the message
            assert log_file.exists()
            content = log_file.read_text()
            assert "Test message" in content
            
            # Clean up file handlers before deleting directory
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
            
    def test_setup_logging_custom_format(self):
        """Test setup_logging with custom format string."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        custom_format = "%(name)s: %(message)s"
        logger = setup_logging(format_string=custom_format)
        
        # Verify format was applied to handlers
        for handler in logger.handlers:
            assert handler.formatter._fmt == custom_format
            
    def test_setup_logging_invalid_level(self):
        """Test setup_logging with invalid log level."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        with pytest.raises(ValueError, match="Invalid log level"):
            setup_logging(level="INVALID")
            
    def test_setup_logging_environment_variable(self):
        """Test setup_logging respects LOGLEVEL environment variable."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Set environment variable
        os.environ['LOGLEVEL'] = 'WARNING'
        try:
            logger = setup_logging()
            assert logger.level == logging.WARNING
        finally:
            del os.environ['LOGLEVEL']
            
    def test_setup_logging_clears_existing_handlers(self):
        """Test that setup_logging clears existing handlers."""
        root_logger = logging.getLogger()
        
        # Add a dummy handler
        dummy_handler = logging.StreamHandler()
        root_logger.addHandler(dummy_handler)
        assert len(root_logger.handlers) >= 1
        
        # Setup logging should clear and re-add
        logger = setup_logging()
        assert dummy_handler not in logger.handlers
        
    def test_setup_logging_all_levels(self):
        """Test setup_logging with all valid log levels."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in levels:
            root_logger = logging.getLogger()
            root_logger.handlers.clear()
            
            logger = setup_logging(level=level)
            expected_level = getattr(logging, level)
            assert logger.level == expected_level


class TestGetLogger:
    """Tests for get_logger function."""
    
    def test_get_logger_basic(self):
        """Test basic get_logger functionality."""
        logger = get_logger("test_module")
        
        assert logger is not None
        assert logger.name == "test_module"
        
    def test_get_logger_initializes_logging(self):
        """Test that get_logger initializes logging if needed."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        logger = get_logger("test_module")
        
        # Root logger should now have handlers
        assert len(root_logger.handlers) > 0
        
    def test_get_logger_multiple_calls(self):
        """Test that multiple get_logger calls return the same logger."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        
        assert logger1 is logger2
        
    def test_get_logger_different_names(self):
        """Test that different logger names return different loggers."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        assert logger1 is not logger2
        assert logger1.name == "module1"
        assert logger2.name == "module2"
        
    def test_get_logger_hierarchy(self):
        """Test logger hierarchy (parent-child relationships)."""
        parent_logger = get_logger("parent")
        child_logger = get_logger("parent.child")
        
        assert child_logger.parent is parent_logger


class TestLoggingIntegration:
    """Integration tests for logging setup and usage."""
    
    def test_logging_to_stderr(self):
        """Test that logs are sent to stderr."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        logger = setup_logging(level="INFO")
        
        # Check that stderr handler is present
        stderr_handlers = [h for h in logger.handlers 
                          if isinstance(h, logging.StreamHandler)]
        assert len(stderr_handlers) > 0
        
    def test_logging_message_propagation(self):
        """Test that logger messages propagate correctly."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        setup_logging()
        logger = get_logger("test_module")
        
        # This should not raise an error
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
    def test_logging_with_file_cleanup(self):
        """Test logging cleanup with file handler."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = setup_logging(log_file=str(log_file))
            
            # Close file handlers for cleanup
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
            
            # File should exist
            assert log_file.exists()
