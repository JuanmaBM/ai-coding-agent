from structlog import get_logger

logger = get_logger(__name__)

class Logger:
    def __init__(self):
        self.log = logger.bind(service="worker")

    def info(self, message, **kwargs):
        """Log an informational message."""
        self.log.info(message, **kwargs)

    def error(self, message, **kwargs):
        """Log an error message."""
        self.log.error(message, **kwargs)

    def debug(self, message, **kwargs):
        """Log a debug message."""
        self.log.debug(message, **kwargs)