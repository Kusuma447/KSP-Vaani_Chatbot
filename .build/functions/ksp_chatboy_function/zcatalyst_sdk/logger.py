from datetime import datetime

class LogLevel:
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    LEVELS = {
        DEBUG: 'DEBUG',
        INFO: 'INFO',
        WARNING: 'WARNING',
        ERROR: 'ERROR',
        CRITICAL: 'CRITICAL'
    }

class Logger:
    def __init__(self,
        name: str = None,
        log_level=LogLevel.WARNING,
        log_format='{timestamp} [{level}] {message}'
    ):
        self.name = name
        self.log_level = log_level
        self.log_format = log_format

    def set_level(self, level: int):
        if level in LogLevel.LEVELS:
            self.log_level = level
        else:
            print(f"Invalid log level: {level}. Log level not changed.")

    def format_message(self, level, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        level_str = LogLevel.LEVELS.get(level, 'UNKNOWN')
        return self.log_format.format(timestamp=timestamp, level=level_str, message=message)

    def log(self, level, message):
        if level >= self.log_level:
            formatted_message = self.format_message(level, message)
            print(formatted_message)

    def debug(self, message):
        self.log(LogLevel.DEBUG, message)

    def info(self, message):
        self.log(LogLevel.INFO, message)

    def warning(self, message):
        self.log(LogLevel.WARNING, message)

    def error(self, message):
        self.log(LogLevel.ERROR, message)

    def critical(self, message):
        self.log(LogLevel.CRITICAL, message)

_global_logger = Logger()

_logger_registry = {}

def get_logger(name: str = None):
    if name is None:
        return _global_logger
    if name not in _logger_registry:
        _logger_registry[name] = Logger(name)
    return _logger_registry[name]
