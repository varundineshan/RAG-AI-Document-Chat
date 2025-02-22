import logging
import os
from datetime import datetime
import json

# Create logs directory in the current working directory
logs_dir = os.path.join(os.getcwd(), 'logs')
try:
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        print(f"Created logs directory at: {logs_dir}")
except Exception as e:
    print(f"Error creating logs directory: {e}")

class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Check if extra fields exist
        session_id = getattr(record, 'session_id', 'N/A')
        file_name = getattr(record, 'file_name', 'N/A')
        question = getattr(record, 'question', 'N/A')
        answer = getattr(record, 'answer', 'N/A')
        
        # Create the log entry
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'session_id': session_id,
            'file_name': file_name,
            'question': question,
            'answer': answer,
            'message': record.getMessage()
        }
        
        return json.dumps(log_entry)

def setup_logger():
    try:
        # Create a logger
        logger = logging.getLogger('app')
        logger.setLevel(logging.INFO)

        # Create handlers
        # File handler
        log_file = os.path.join(logs_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # Set custom formatter
        file_handler.setFormatter(CustomFormatter())

        # Remove any existing handlers
        logger.handlers = []

        # Add handler to the logger
        logger.addHandler(file_handler)
        
        print(f"Logger setup complete. Logging to: {log_file}")
        return logger
    except Exception as e:
        print(f"Error setting up logger: {e}")
        return logging.getLogger('app')

# Initialize logger
logger = setup_logger() 