"""
File Log Handler Module

Provides enhanced logging capabilities for the evaluation framework,
including file-based logging with rotation and structured output.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


class FileLogHandler:
    """Manages file-based logging for the evaluation framework.

    Provides methods to set up file logging in addition to console logging,
    with automatic directory creation and timestamped log files.
    """

    def __init__(
        self,
        output_dir: Path,
        log_level: int = logging.INFO,
        log_format: str | None = None,
    ):
        """Initialize the file log handler.

        Args:
            output_dir: Directory where log files will be saved
            log_level: Logging level (default: INFO)
            log_format: Custom log format string (optional)
        """
        self.output_dir = output_dir
        self.log_level = log_level
        self.log_format = log_format or "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self._handlers: list[logging.Handler] = []

    def setup_logging(
        self,
        console_output: bool = True,
        file_output: bool = True,
        log_filename: str | None = None,
    ) -> logging.Logger:
        """Set up complete logging configuration.

        Args:
            console_output: Whether to output logs to console
            file_output: Whether to output logs to file
            log_filename: Custom log filename (without .log extension).
                         If None, uses timestamp-based filename.

        Returns:
            Configured root logger instance
        """
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)

        # Clear any existing handlers
        root_logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(self.log_format)

        # Add console handler if requested
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            self._handlers.append(console_handler)

        # Add file handler if requested
        if file_output:
            if log_filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_filename = f"evaluation_{timestamp}.log"

            log_file = self.output_dir / log_filename
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            self._handlers.append(file_handler)

        return root_logger

    def add_test_specific_logger(
        self,
        test_id: str,
        test_name: str | None = None,
    ) -> logging.Logger:
        """Create a test-specific logger with its own file.

        Useful for isolating logs from individual test cases.

        Args:
            test_id: Unique test identifier
            test_name: Human-readable test name (optional)

        Returns:
            Logger instance configured for this specific test
        """
        # Create test-specific log directory
        test_log_dir = self.output_dir / "test_logs" / test_id
        test_log_dir.mkdir(parents=True, exist_ok=True)

        # Create test-specific log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{test_name or test_id}_{timestamp}.log"
        log_file = test_log_dir / log_filename

        # Create logger
        logger = logging.getLogger(f"test.{test_id}")
        logger.setLevel(self.log_level)
        logger.propagate = False  # Don't propagate to root logger

        # Add file handler
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(self.log_level)
        formatter = logging.Formatter(self.log_format)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Also add console handler for real-time monitoring
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger

    def add_step_logger(
        self,
        test_id: str,
        step_name: str,
    ) -> logging.Logger:
        """Create a step-specific logger for detailed step tracking.

        Args:
            test_id: Test identifier
            step_name: Name of the step (e.g., "config_injection", "execution")

        Returns:
            Logger instance for this step
        """
        step_log_dir = self.output_dir / "test_logs" / test_id / "steps"
        step_log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = step_log_dir / f"{step_name}_{timestamp}.log"

        logger = logging.getLogger(f"test.{test_id}.step.{step_name}")
        logger.setLevel(logging.DEBUG)  # Steps use DEBUG level for detail
        logger.propagate = False

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    def close_all(self) -> None:
        """Close all log handlers and release resources."""
        for handler in self._handlers:
            handler.close()
        self._handlers.clear()

    @staticmethod
    def log_config(logger: logging.Logger, config: dict) -> None:
        """Log configuration details in a structured format.

        Args:
            logger: Logger instance
            config: Configuration dictionary to log
        """
        logger.info("=" * 60)
        logger.info("Configuration Details")
        logger.info("=" * 60)
        for key, value in config.items():
            if isinstance(value, dict):
                logger.info(f"  {key}:")
                for sub_key, sub_value in value.items():
                    logger.info(f"    {sub_key}: {sub_value}")
            else:
                logger.info(f"  {key}: {value}")
        logger.info("=" * 60)

    @staticmethod
    def log_section(logger: logging.Logger, section_name: str) -> None:
        """Log a section separator for better log readability.

        Args:
            logger: Logger instance
            section_name: Name of the section
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info(f" {section_name}")
        logger.info("=" * 60)
        logger.info("")

    @staticmethod
    def log_error_with_context(
        logger: logging.Logger,
        error: Exception,
        context: dict | None = None,
    ) -> None:
        """Log an error with additional context information.

        Args:
            logger: Logger instance
            error: Exception that occurred
            context: Additional context dictionary (optional)
        """
        logger.error(f"Error: {type(error).__name__}: {error}")
        if context:
            logger.error("Context:")
            for key, value in context.items():
                logger.error(f"  {key}: {value}")
