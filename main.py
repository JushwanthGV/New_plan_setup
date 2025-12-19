import sys
import os
import logging
import io


# --- FIX ENCODING ON WINDOWS ---
if os.name == 'nt':
    # Force Python to use UTF-8
    os.system('chcp 65001 >nul')

    # Wrap stdout/stderr to enforce UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    # Sometimes required for VSCode terminal
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


import time
from dotenv import load_dotenv
from pathlib import Path


from utils.outlook_connector import OutlookConnector
from utils.document_parser import DocumentParser
from utils.data_exporter import DataExporter
from agents.email_monitor_agent import EmailMonitorAgent
from agents.document_validator_agent import DocumentValidatorAgent
from agents.requestor_interaction_agent import RequestorInteractionAgent
from agents.data_export_agent import DataExportAgent
from graph.workflow import EmailProcessingWorkflow
# --- ADDED IMPORTS FOR EXCEPTION HANDLER ---
from mock_queue.queue_manager import QueueManager
from agents.bp_exception_handler import BPExceptionHandler


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/email_processing.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Use stdout explicitly
    ]
)


logger = logging.getLogger(__name__)



# ---------------------------------------------------------
# NEW: Clean helper function for tick/cross agent status
# ---------------------------------------------------------
def format_status(ok: bool, message: str = ""):
    """Return ✓ or ✗ with clean message."""
    if ok:
        return f"✓ {message}"
    else:
        return f"✗ {message}"



def load_configuration():
    """Load configuration from environment variables"""
    load_dotenv()
    
    config = {
        'email_address': os.getenv('EMAIL_ADDRESS'),
        'app_password': os.getenv('APP_PASSWORD'),
        'email_provider': os.getenv('EMAIL_PROVIDER', 'gmail').lower(),
        'monitor_sender': os.getenv('MONITOR_SENDER'),
        'monitor_subject': os.getenv('MONITOR_SUBJECT'),
        
        'download_path': os.getenv('DOWNLOAD_PATH', './data/inbox_attachments'),
        'validated_data_path': os.getenv('VALIDATED_DATA_PATH', './data/validated_documents'),
        'pending_requests_path': os.getenv('PENDING_REQUESTS_PATH', './data/pending_requests'),
        'export_path': os.getenv('EXPORT_PATH', './data/network_export'),
        'export_logs_path': os.getenv('EXPORT_LOGS_PATH', './data/export_logs'),
        
        'groq_api_key': os.getenv('GROQ_API_KEY'),
        'groq_model': os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'),
        'mandatory_fields': os.getenv('MANDATORY_FIELDS', 'name,address,phone_number').split(','),
        
        'check_interval': int(os.getenv('CHECK_INTERVAL', 300)),
        'log_exports': os.getenv('LOG_EXPORTS', 'true').lower() == 'true'
    }
    
    required_fields = [
        'email_address',
        'app_password',
        'monitor_sender',
        'monitor_subject',
        'groq_api_key'
    ]
    missing_fields = [field for field in required_fields if not config.get(field)]
    
    if missing_fields:
        raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")
    
    config['mandatory_fields'] = [field.strip() for field in config['mandatory_fields']]
    
    return config



def setup_environment(config: dict):
    """UPDATED: Consolidated directory setup"""
    directories = [
        config['download_path'],
        config['validated_data_path'],
        config['pending_requests_path'],
        config['export_path'],
        config['export_logs_path'],
        './data/logs',  # NEW: Centralized logs
        './data',  # Ensure data root exists
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Directory ready: {directory}")



def ensure_queue_database_exists():
    """Ensure queue database file and directory exist"""
    import json
    
    # UPDATED: Use centralized data/queue.json
    queue_path = Path("./data/queue.json")
    
    # Create directory if it doesn't exist
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create empty queue file if it doesn't exist
    if not queue_path.exists():
        with open(queue_path, 'w', encoding='utf-8') as f:
            json.dump([], f)
        logger.info(f"✓ Created queue database: {queue_path}")
    else:
        logger.info(f"✓ Queue database exists: {queue_path}")
    
    return str(queue_path)



def ensure_retry_registry_exists():
    """NEW: Ensure retry registry exists"""
    import json
    
    registry_path = Path("./data/retry_registry.json")
    
    if not registry_path.exists():
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        logger.info(f"✓ Created retry registry: {registry_path}")
    else:
        logger.info(f"✓ Retry registry exists: {registry_path}")
    
    return str(registry_path)



def run_once(workflow: EmailProcessingWorkflow):
    logger.info("\n" + "="*80)
    logger.info("STARTING EMAIL PROCESSING CYCLE")
    logger.info("="*80)
    
    result = workflow.run()
    
    logger.info("\n" + "="*80)
    logger.info("CYCLE COMPLETED")
    logger.info("="*80)
    
    return result


def run_continuous(workflow: EmailProcessingWorkflow, exception_handler, check_interval: int):
    logger.info(f"Starting continuous monitoring (checking every {check_interval} seconds)")
    logger.info("Press Ctrl+C to stop")
    
    try:
        while True:
            run_once(workflow)
            
            # --- ADDED: Run Exception Handler Logic ---
            logger.info("Checking for Worker Exceptions...")
            exception_handler.process_exceptions()
            
            logger.info(f"⏳ Waiting {check_interval} seconds until next check...")
            time.sleep(check_interval)
    except KeyboardInterrupt:
        logger.info("ℹ️  Monitoring stopped by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error in continuous monitoring: {str(e)}")
        raise



def main():
    try:
        logger.info("Loading configuration...")
        config = load_configuration()
        
        setup_environment(config)


        # Initialize all agents
        logger.info("Connecting to email service...")
        outlook_connector = OutlookConnector(
            email_address=config['email_address'],
            app_password=config['app_password'],
            provider=config['email_provider']
        )
        
        logger.info("Initializing Document Parser...")
        document_parser = DocumentParser()
        
        monitor_config = {
            'sender': config['monitor_sender'],
            'subject': config['monitor_subject'],
            'download_path': config['download_path']
        }
        email_monitor = EmailMonitorAgent(outlook_connector, monitor_config)
        
        logger.info("Initializing AGENT 2: Document Validator Agent (Groq)...")
        document_validator = DocumentValidatorAgent(
            groq_api_key=config['groq_api_key'],
            mandatory_fields=config['mandatory_fields'],
            validated_data_path=config['validated_data_path'],
            model=config['groq_model']
        )
        
        logger.info("Initializing AGENT 3: Requestor Interaction Agent...")
        requestor_interaction = RequestorInteractionAgent(
            outlook_connector=outlook_connector,
            tracking_path=config['pending_requests_path']
        )
        
        logger.info("Initializing Data Exporter...")
        data_exporter = DataExporter(config['export_path'])


        logger.info("Initializing AGENT 4: Data Export Agent...")
        data_export = DataExportAgent(
            data_exporter=data_exporter,
            log_exports=config['log_exports'],
            log_path=config['export_logs_path']
        )

        # --- ADDED: Ensure queue database and retry registry exist ---
        logger.info("Ensuring queue database exists...")
        queue_db_path = ensure_queue_database_exists()
        
        logger.info("Ensuring retry registry exists...")
        retry_registry_path = ensure_retry_registry_exists()

        # --- MODIFIED: Initialize Agent 5 with explicit path ---
        logger.info("Initializing AGENT 5: BP Exception Handler...")
        queue_manager = QueueManager(queue_db_path)
        exception_handler = BPExceptionHandler(
            queue_manager=queue_manager,
            requestor_interaction_agent=requestor_interaction,
            outlook_connector=outlook_connector
        )
        
        # Build workflow - UPDATED: Pass exception handler
        logger.info("Building complete Agentic AI Workflow...")
        workflow = EmailProcessingWorkflow(
            email_monitor_agent=email_monitor,
            document_validator_agent=document_validator,
            requestor_interaction_agent=requestor_interaction,
            data_export_agent=data_export,
            document_parser=document_parser,
            bp_exception_handler=exception_handler  # NEW: Pass exception handler
        )
        
        # ---------------------------------------------------------
        # NEW: Agent Status Overview (with ✓ ✗ indicators)
        # ---------------------------------------------------------
        s1 = email_monitor.get_status()
        s2 = document_validator.get_status()
        s3 = requestor_interaction.get_status()
        s4 = data_export.get_status()


        logger.info("\n" + "="*80)
        logger.info("AGENT STATUS:")
        
        logger.info("  " + format_status(True,  f"Agent 1: {s1['agent']}"))
        logger.info("  " + format_status(True,  f"Agent 2: {s2['agent']}"))
        logger.info("  " + format_status(True,  f"Agent 3: {s3['agent']}"))


        if s4.get("export_path_accessible", False):
            logger.info("  " + format_status(True,  f"Agent 4: {s4['agent']}"))
            logger.info(f"     Export Path: {s4['export_path']}")
        else:
            logger.info("  " + format_status(False, f"Agent 4: {s4['agent']} (export path inaccessible)"))
        
        # --- ADDED: Status for Agent 5 ---
        logger.info("  " + format_status(True, "Agent 5: BP Exception Handler"))
        logger.info(f"     Queue Database: {queue_db_path}")
        logger.info(f"     Retry Registry: {retry_registry_path}")

        logger.info("="*80)


        # Run continuous cycle
        # --- UPDATED: Pass exception_handler ---
        run_continuous(workflow, exception_handler, config['check_interval'])


    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}", exc_info=True)
        raise



if __name__ == "__main__":
    main()