"""
Agent 5: Blue Prism Exception Handler
Monitors BP queue for exceptions and handles retries
"""

import logging
import time
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Add parent directory to path to import from mock_queue
sys.path.append(str(Path(__file__).parent.parent))

from mock_queue.queue_manager import QueueManager
from mock_queue.config import *

logger = logging.getLogger(__name__)

class BPExceptionHandler:
    """Agent 5 - Monitors BP exceptions and handles retries"""
    
    def __init__(self, queue_manager: QueueManager, 
                 requestor_interaction_agent,
                 outlook_connector):
        """
        Initialize BP Exception Handler
        
        Args:
            queue_manager: Instance of QueueManager
            requestor_interaction_agent: Agent 3 for sending emails
            outlook_connector: Email connector
        """
        self.queue = queue_manager
        self.interaction_agent = requestor_interaction_agent
        self.outlook = outlook_connector
        self.max_retries = MAX_RETRY_ATTEMPTS
        logger.info("BP Exception Handler (Agent 5) initialized")
    
    def simulate_vdi_restart(self):
        """Simulate VDI restart"""
        logger.info(f"🔄 Restarting {VDI_NAME}...")
        logger.info("   ► Sending shutdown signal...")
        time.sleep(1)
        logger.info("   ► Waiting for clean shutdown...")
        time.sleep(1)
        logger.info("   ► Starting VDI...")
        time.sleep(1)
        logger.info(f"✓ {VDI_NAME} restarted successfully")
    
    def generate_new_plan_id(self, original_plan_id: str, retry_count: int) -> str:
        """
        Generate new Plan ID for retry
        
        Args:
            original_plan_id: Original Plan ID that failed
            retry_count: Current retry attempt number
            
        Returns:
            New Plan ID
        """
        import random
        import string
        
        # Generate new 7-character alphanumeric ID
        chars = string.ascii_uppercase + string.digits
        new_id = ''.join(random.choices(chars, k=PLAN_ID_LENGTH))
        
        logger.info(f"Generated new Plan ID: {new_id} (Original: {original_plan_id}, Retry: {retry_count})")
        return new_id
    
    def handle_plan_id_exists_exception(self, item: Dict[str, Any]) -> bool:
        """
        Handle 'Plan ID Already Exists' exception
        
        Args:
            item: Queue item with exception
            
        Returns:
            True if retry was queued, False if max retries reached
        """
        item_id = item['id']
        plan_id = item['plan_id']
        original_plan_id = item.get('original_plan_id', plan_id)
        retry_count = item.get('retry_count', 0)
        data = item['data']
        
        logger.info(f"{'='*80}")
        logger.info(f"🔍 HANDLING EXCEPTION: Plan ID Already Exists")
        logger.info(f"   Item ID: {item_id}")
        logger.info(f"   Current Plan ID: {plan_id}")
        logger.info(f"   Retry Count: {retry_count}")
        logger.info(f"{'='*80}")
        
        # Check if max retries reached
        if retry_count >= self.max_retries:
            logger.error(f"❌ Max retries ({self.max_retries}) reached for {item_id}")
            logger.error(f"   Escalating to user...")
            
            # Send escalation email
            self._send_escalation_email(item)
            
            return False
        
        # Generate new Plan ID
        new_plan_id = self.generate_new_plan_id(original_plan_id, retry_count + 1)
        
        # Update retry history
        retry_history = item.get('retry_history', [])
        retry_history.append({
            'attempt': retry_count + 1,
            'plan_id': plan_id,
            'exception': EXCEPTION_PLAN_EXISTS,
            'vdi': item['vdi_assigned'],
            'timestamp': datetime.now().isoformat()
        })
        
        # Send retry notification email
        self._send_retry_notification_email(item, new_plan_id, retry_count + 1)
        
        # Restart VDI
        self.simulate_vdi_restart()
        
        # Add new item to queue with incremented retry count
        self.queue.add_item(
            data=data,
            plan_id=new_plan_id,
            original_plan_id=original_plan_id,
            retry_count=retry_count + 1,
            retry_history=retry_history
        )
        
        logger.info(f"✓ Retry queued with new Plan ID: {new_plan_id}")
        logger.info(f"{'='*80}\n")
        
        return True
    
    def handle_data_error_exception(self, item: Dict[str, Any]):
        """
        Handle data validation error exception
        
        Args:
            item: Queue item with exception
        """
        logger.info(f"{'='*80}")
        logger.info(f"⚠️  HANDLING EXCEPTION: Data Validation Error")
        logger.info(f"   Item ID: {item['id']}")
        logger.info(f"   Exception: {item['exception_reason']}")
        logger.info(f"{'='*80}")
        
        # Send data error email immediately (no retry)
        self._send_data_error_email(item)
        
        logger.info(f"✓ Data error notification sent to user")
        logger.info(f"{'='*80}\n")
    
    def _send_retry_notification_email(self, item: Dict[str, Any], 
                                       new_plan_id: str, retry_attempt: int):
        """Send email notification about retry"""
        data = item['data']
        name = data.get('name', 'Customer')
        old_plan_id = item['plan_id']
        
        email_body = f"""Dear {name},

Your plan setup submission encountered an issue and is being automatically retried.

ISSUE DETECTED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  Plan ID "{old_plan_id}" already exists in the system.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AUTOMATIC RETRY IN PROGRESS:
✓ New Plan ID Generated: {new_plan_id}
✓ Retry Attempt: {retry_attempt} of {self.max_retries}
✓ Processing System: VDI_Server_01 (restarted)

NO ACTION REQUIRED from you. We are automatically retrying your submission 
with the new Plan ID. You will receive confirmation once processing is complete.

TRACKING INFORMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Queue Item ID: {item['id']}
Original Plan ID: {item.get('original_plan_id', old_plan_id)}
Previous Plan ID: {old_plan_id}
New Plan ID: {new_plan_id}
Retry Attempt: {retry_attempt}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If you have any questions, please contact our support team.

Best regards,
JushQuant Associates - Automated Plan Setup System
"""
        
        try:
            # Get email from data or use default
            recipient = data.get('_requester_email', 'prajush01@gmail.com')
            
            self.outlook.send_email(
                to=recipient,
                subject=f"Plan Setup - Automatic Retry #{retry_attempt}",
                body=email_body
            )
            logger.info(f"✓ Retry notification email sent to {recipient}")
        except Exception as e:
            logger.error(f"✗ Failed to send retry notification: {str(e)}")
    
    def _send_escalation_email(self, item: Dict[str, Any]):
        """Send email for max retries reached"""
        data = item['data']
        name = data.get('name', 'Customer')
        retry_history = item.get('retry_history', [])
        
        # Build attempt history
        attempt_history = ""
        for i, attempt in enumerate(retry_history, 1):
            attempt_history += f"Attempt {i}: Plan ID '{attempt['plan_id']}' → Failed ({attempt['exception']})\n"
        
        email_body = f"""Dear {name},

Your plan setup submission has failed after multiple automatic retry attempts.

ISSUE SUMMARY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Plan ID conflict detected on all {len(retry_history)} attempts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RETRY HISTORY:
{attempt_history}

This indicates a systematic conflict with existing plan records.

NEXT STEPS:
Please contact our support team with the following information:

Tracking ID: {item['id']}
Original Plan ID: {item.get('original_plan_id')}
Customer Name: {name}
Submission Date: {item.get('created_at')}

Our team will investigate and contact you within 24 hours.

Best regards,
JushQuant Associates - Automated Plan Setup System
"""
        
        try:
            recipient = data.get('_requester_email', 'prajush01@gmail.com')
            
            self.outlook.send_email(
                to=recipient,
                subject=f"URGENT: Plan Setup Failed After {len(retry_history)} Attempts",
                body=email_body
            )
            logger.info(f"✓ Escalation email sent to {recipient}")
        except Exception as e:
            logger.error(f"✗ Failed to send escalation email: {str(e)}")
    
    def _send_data_error_email(self, item: Dict[str, Any]):
        """Send email for data validation errors"""
        data = item['data']
        name = data.get('name', 'Customer')
        exception = item.get('exception_reason', 'Unknown error')
        
        email_body = f"""Dear {name},

Your plan setup submission could not be processed due to a data validation error.

ISSUE DETECTED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  {exception}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOUR SUBMITTED DATA:
Name: {data.get('name', 'N/A')}
Address: {data.get('address', 'N/A')}
Phone Number: {data.get('phone_number', 'N/A')}
Plan ID: {item['plan_id']}

ACTION REQUIRED:
Please review your information and resubmit your application with corrected data.

TRACKING INFORMATION:
Queue Item ID: {item['id']}
Submission Date: {item.get('created_at')}

If you believe this is an error, please contact our support team.

Best regards,
JushQuant Associates - Automated Plan Setup System
"""
        
        try:
            recipient = data.get('_requester_email', 'prajush01@gmail.com')
            
            self.outlook.send_email(
                to=recipient,
                subject=f"Action Required: Plan Setup Data Error",
                body=email_body
            )
            logger.info(f"✓ Data error email sent to {recipient}")
        except Exception as e:
            logger.error(f"✗ Failed to send data error email: {str(e)}")
    
    def process_exceptions(self):
        """Check queue for exceptions and handle them"""
        exception_items = self.queue.get_items_by_status('Exception')
        
        if not exception_items:
            return
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 Found {len(exception_items)} exception(s) to process")
        logger.info(f"{'='*80}\n")
        
        for item in exception_items:
            exception_reason = item.get('exception_reason', '')
            
            if EXCEPTION_PLAN_EXISTS in exception_reason:
                # Handle Plan ID conflict with retry
                self.handle_plan_id_exists_exception(item)
                
            elif EXCEPTION_DATA_ERROR in exception_reason:
                # Handle data error without retry
                self.handle_data_error_exception(item)
            
            else:
                # Unknown exception type
                logger.warning(f"⚠️  Unknown exception type: {exception_reason}")
    
    def run_continuous(self, poll_interval: int = 10):
        """
        Run exception handler in continuous mode
        
        Args:
            poll_interval: Seconds to wait between polls
        """
        logger.info(f"{'='*80}")
        logger.info(f"🚀 BP EXCEPTION HANDLER (AGENT 5) STARTED")
        logger.info(f"⏱️  Poll Interval: {poll_interval} seconds")
        logger.info(f"🔄 Max Retry Attempts: {self.max_retries}")
        logger.info(f"{'='*80}\n")
        logger.info("Press Ctrl+C to stop\n")
        
        try:
            while True:
                self.process_exceptions()
                
                logger.info(f"💤 Waiting {poll_interval} seconds before next check...\n")
                time.sleep(poll_interval)
                    
        except KeyboardInterrupt:
            logger.info("\n⏹️  Exception Handler stopped by user")
        except Exception as e:
            logger.error(f"\n✗ Exception Handler error: {str(e)}")
            raise
# Force it to look in the project root
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

email_address = os.getenv('EMAIL_ADDRESS')
app_password = os.getenv('APP_PASSWORD')

def main():
    """Main entry point for Exception Handler"""
    import sys
    from pathlib import Path
    
    # Add parent directory to import agents
    sys.path.append(str(Path(__file__).parent.parent))
    
    from utils.outlook_connector import OutlookConnector
    from agents.requestor_interaction_agent import RequestorInteractionAgent
    
    # Initialize connectors
    outlook = OutlookConnector(email_address=email_address, app_password=app_password)
    
    # Initialize agents
    interaction_agent = RequestorInteractionAgent(outlook)
    queue = QueueManager(QUEUE_DATABASE)
    
    # Initialize and run Agent 5
    handler = BPExceptionHandler(queue, interaction_agent, outlook)
    handler.run_continuous(poll_interval=10)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [AGENT 5] - %(message)s',
        handlers=[
            logging.FileHandler(LOG_DIR / "bp_exception_handler.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    main()