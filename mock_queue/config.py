"""
Configuration for Mock Blue Prism Queue System
"""
import os
import pathlib

# Base directory for the project
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

# Queue Settings - CORRECT PATH (stores in data/queue.json)
QUEUE_DATABASE = BASE_DIR / "data" / "queue.json"
VDI_NAME = "VDI_Server_01"
MAX_RETRY_ATTEMPTS = 2  # Total 2 attempts (original + 1 retry)

# Plan ID Settings
PLAN_ID_LENGTH = 7  # 7 character alphanumeric IDs

# Dashboard Settings
DEFAULT_REFRESH_RATE = 2  # seconds
REFRESH_OPTIONS = {
    'F': 2,   # Fast
    'M': 5,   # Medium
    'S': 10,  # Slow
}

# Worker Settings
WORKER_PROCESSING_TIME = 3  # seconds to simulate BP processing
VDI_RESTART_TIME = 3  # seconds to simulate VDI restart

# Exception Types
EXCEPTION_PLAN_EXISTS = "Plan ID Already Exists"
EXCEPTION_DATA_ERROR = "Invalid Data Format"

# Email Settings (inherited from main system)
EMAIL_FROM_AGENT = True  # Agent 5 sends emails via RequestorInteractionAgent

