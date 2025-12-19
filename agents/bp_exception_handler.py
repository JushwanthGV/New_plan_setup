"""
Agent 5: Blue Prism Exception Handler
Monitors BP queue for exceptions and handles retries with persistent registry
UPDATED: Uses retry registry to prevent infinite loops and handle duplicate submissions
"""

import logging
import time
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# UPDATED: Centralized retry registry path
RETRY_REGISTRY_PATH = PROJECT_ROOT / "data" / "retry_registry.json"

sys.path.append(str(Path(__file__).parent.parent))

from mock_queue.queue_manager import QueueManager
from mock_queue.config import *

logger = logging.getLogger(__name__)

class BPExceptionHandler:
    """Agent 5 - Monitors BP exceptions and handles retries with persistent registry"""
    
    def __init__(self, queue_manager, requestor_interaction_agent, outlook_connector=None):
        self.queue = queue_manager
        self.requestor_interaction_agent = requestor_interaction_agent
        self.outlook = outlook_connector
        self.max_retries = MAX_RETRY_ATTEMPTS
        
        # Initialize retry registry
        self._ensure_registry_exists()
        
        logger.info("BP Exception Handler (Agent 5) initialized with retry registry")
    
    def _ensure_registry_exists(self):
        """Create retry registry if it doesn't exist"""
        if not RETRY_REGISTRY_PATH.exists():
            RETRY_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(RETRY_REGISTRY_PATH, 'w') as f:
                json.dump({}, f)
            logger.info(f"Created retry registry: {RETRY_REGISTRY_PATH}")
    
    def _load_registry(self) -> Dict:
        """Load retry registry from disk"""
        try:
            with open(RETRY_REGISTRY_PATH, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_registry(self, registry: Dict):
        """Save retry registry to disk"""
        with open(RETRY_REGISTRY_PATH, 'w') as f:
            json.dump(registry, f, indent=2)
    
    def check_duplicate_submission(self, plan_id: str, requester_email: str) -> Optional[Dict]:
        """
        NEW: Check if this Plan ID was already escalated
        
        Args:
            plan_id: Plan ID from incoming email
            requester_email: Email address of requestor
            
        Returns:
            Registry entry if found and escalated, None otherwise
        """
        registry = self._load_registry()
        
        # Check if this plan_id exists as original_plan_id in registry
        if plan_id in registry:
            entry = registry[plan_id]
            if entry['status'] == 'ESCALATED':
                logger.warning(f"🚫 DUPLICATE SUBMISSION DETECTED: Plan ID {plan_id}")
                logger.warning(f"   This Plan ID was already escalated")
                logger.warning(f"   Attempts made: {entry['retry_count']}")
                return entry
        
        return None
    
    def _check_retry_status(self, original_plan_id: str) -> Dict:
        """
        Check retry status for an original plan ID
        
        Returns:
            {
                'retry_count': int,
                'status': 'IN_PROGRESS'|'ESCALATED'|'COMPLETED',
                'attempts': [list of attempts]
            }
        """
        registry = self._load_registry()
        
        if original_plan_id not in registry:
            return {
                'retry_count': 0,
                'status': 'IN_PROGRESS',
                'attempts': []
            }
        
        return registry[original_plan_id]
    
    def _update_registry(self, original_plan_id: str, new_plan_id: str, 
                        retry_count: int, status: str, requester_email: str = None):
        """
        Update retry registry with new attempt
        
        UPDATED: Now stores requester_email for duplicate detection
        """
        registry = self._load_registry()
        
        if original_plan_id not in registry:
            registry[original_plan_id] = {
                'retry_count': 0,
                'status': 'IN_PROGRESS',
                'attempts': [],
                'first_seen': datetime.now().isoformat(),
                'requester_email': requester_email or 'unknown'
            }
        
        registry[original_plan_id]['retry_count'] = retry_count
        registry[original_plan_id]['status'] = status
        registry[original_plan_id]['attempts'].append({
            'plan_id': new_plan_id,
            'timestamp': datetime.now().isoformat(),
            'retry_number': retry_count
        })
        registry[original_plan_id]['last_updated'] = datetime.now().isoformat()
        
        # Update email if provided
        if requester_email:
            registry[original_plan_id]['requester_email'] = requester_email
        
        self._save_registry(registry)
        logger.info(f"Registry updated: {original_plan_id} → Retry {retry_count}, Status: {status}")
    
    def simulate_vdi_restart(self):
        """Simulate VDI restart"""
        logger.info(f"🔄 Restarting {VDI_NAME}...")
        logger.info("   ▶ Sending shutdown signal...")
        time.sleep(1)
        logger.info("   ▶ Waiting for clean shutdown...")
        time.sleep(1)
        logger.info("   ▶ Starting VDI...")
        time.sleep(1)
        logger.info(f"✅ {VDI_NAME} restarted successfully")
    
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
        
        chars = string.ascii_uppercase + string.digits
        new_id = ''.join(random.choices(chars, k=PLAN_ID_LENGTH))
        
        logger.info(f"Generated new Plan ID: {new_id} (Original: {original_plan_id}, Retry: {retry_count})")
        return new_id
    
    def handle_plan_id_exists_exception(self, item: Dict[str, Any]) -> bool:
        """
        Handle 'Plan ID Already Exists' exception with registry-based retry tracking
        
        Args:
            item: Queue item with exception
            
        Returns:
            True if retry was queued, False if max retries reached
        """
        item_id = item['id']
        plan_id = item['plan_id']
        original_plan_id = item.get('original_plan_id', plan_id)
        data = item['data']
        requester_email = data.get('_requester_email', 'prajush01@gmail.com')
        
        logger.info(f"{'='*80}")
        logger.info(f"🔍 HANDLING EXCEPTION: Plan ID Already Exists")
        logger.info(f"   Item ID: {item_id}")
        logger.info(f"   Current Plan ID: {plan_id}")
        logger.info(f"   Original Plan ID: {original_plan_id}")
        logger.info(f"{'='*80}")
        
        # Check registry for retry status
        retry_status = self._check_retry_status(original_plan_id)
        
        # If already escalated in registry, skip processing
        if retry_status['status'] == 'ESCALATED':
            logger.warning(f"⚠️  Original Plan ID {original_plan_id} already ESCALATED in registry")
            logger.warning(f"   Skipping duplicate exception processing")
            # Mark queue item as escalated
            self.queue.update_item(item_id, {'status': 'Escalated'})
            return False
        
        current_retry_count = retry_status['retry_count']
        
        logger.info(f"   Registry Retry Count: {current_retry_count}")
        logger.info(f"   Registry Status: {retry_status['status']}")
        
        # Check if max retries reached
        if current_retry_count >= self.max_retries:
            logger.error(f"❌ Max retries ({self.max_retries}) reached for Original Plan ID: {original_plan_id}")
            logger.error(f"   Escalating to user...")
            
            # Update registry to ESCALATED
            self._update_registry(original_plan_id, plan_id, current_retry_count, 'ESCALATED', requester_email)
            
            # Send escalation email with ALL attempted Plan IDs
            self._send_escalation_email(item, retry_status)
            
            # Mark queue item as escalated
            self.queue.update_item(item_id, {'status': 'Escalated'})
            
            return False
        
        # Generate new Plan ID
        new_retry_count = current_retry_count + 1
        new_plan_id = self.generate_new_plan_id(original_plan_id, new_retry_count)
        
        # Update registry with new attempt
        self._update_registry(original_plan_id, new_plan_id, new_retry_count, 'IN_PROGRESS', requester_email)
        
        # Send retry notification email
        self._send_retry_notification_email(item, new_plan_id, new_retry_count, retry_status)
        
        # Restart VDI
        self.simulate_vdi_restart()
        
        # Add new item to queue with incremented retry count
        self.queue.add_item(
            data=data,
            plan_id=new_plan_id,
            original_plan_id=original_plan_id,
            retry_count=new_retry_count,
            retry_history=item.get('retry_history', []) + [{
                'attempt': new_retry_count,
                'plan_id': plan_id,
                'exception': EXCEPTION_PLAN_EXISTS,
                'vdi': item['vdi_assigned'],
                'timestamp': datetime.now().isoformat()
            }]
        )
        
        logger.info(f"✅ Retry queued with new Plan ID: {new_plan_id}")
        
        # Mark original exception item as processed
        self.queue.update_item(item_id, {'status': 'Retry Queued'})
        
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
        
        # Mark as user notified
        self.queue.update_item(item['id'], {'status': 'User Notified'})
        
        logger.info(f"✅ Data error notification sent to user")
        logger.info(f"{'='*80}\n")
    
    def _send_retry_notification_email(self, item: Dict[str, Any], 
                                       new_plan_id: str, retry_attempt: int,
                                       retry_status: Dict):
        """Send email notification about retry"""
        data = item['data']
        name = data.get('name', 'Customer')
        old_plan_id = item['plan_id']
        original_plan_id = item.get('original_plan_id', old_plan_id)
        
        # Build attempt history
        attempt_history = ""
        for attempt in retry_status['attempts']:
            attempt_history += f"Attempt {attempt['retry_number']}: Plan ID '{attempt['plan_id']}'\n"
        
        email_body = f"""Dear {name},

Your plan setup submission encountered an issue and is being automatically retried.

ISSUE DETECTED:
┌────────────────────────────────────────────────┐
│ ⚠️  Plan ID "{old_plan_id}" already exists     │
│    in the system.                              │
└────────────────────────────────────────────────┘

AUTOMATIC RETRY IN PROGRESS:
✓ New Plan ID Generated: {new_plan_id}
✓ Retry Attempt: {retry_attempt} of {self.max_retries}
✓ Processing System: VDI_Server_01 (restarted)

NO ACTION REQUIRED from you. We are automatically retrying your submission 
with the new Plan ID. You will receive confirmation once processing is complete.

TRACKING INFORMATION:
┌────────────────────────────────────────────────┐
│ Queue Item ID: {item['id']}
│ Original Plan ID: {original_plan_id}
│ Previous Plan ID: {old_plan_id}
│ New Plan ID: {new_plan_id}
│ Retry Attempt: {retry_attempt}
│
│ Retry History:
│ {attempt_history}
└────────────────────────────────────────────────┘

If you have any questions, please contact our support team.

Best regards,
JushQuant Associates - Automated Plan Setup System
"""
        
        try:
            recipient = data.get('_requester_email', 'prajush01@gmail.com')
            
            self.outlook.send_email(
                to=recipient,
                subject=f"Plan Setup - Automatic Retry #{retry_attempt}",
                body=email_body
            )
            logger.info(f"✅ Retry notification email sent to {recipient}")
        except Exception as e:
            logger.error(f"❌ Failed to send retry notification: {str(e)}")
    
    def _send_escalation_email(self, item: Dict[str, Any], retry_status: Dict):
        """Send email for max retries reached with ALL attempted Plan IDs"""
        data = item['data']
        name = data.get('name', 'Customer')
        original_plan_id = item.get('original_plan_id', item['plan_id'])
        
        # Build complete attempt history
        attempt_history = ""
        for idx, attempt in enumerate(retry_status['attempts'], 1):
            attempt_history += f"Attempt {idx}: Plan ID '{attempt['plan_id']}' → Failed (Plan ID Already Exists)\n"
        
        email_body = f"""Dear {name},

Your plan setup submission has failed after multiple automatic retry attempts.

ISSUE SUMMARY:
┌──────────────────────────────────────────────────────────┐
│ ❌ Plan ID conflict detected on ALL {len(retry_status['attempts'])} attempts    │
└──────────────────────────────────────────────────────────┘

ORIGINAL PLAN ID PROVIDED:
{original_plan_id}

RETRY HISTORY (All Failed):
{attempt_history}

REASON FOR FAILURE:
This indicates a systematic conflict with existing plan records. 
Possible causes:
• The document may be corrupted or incomplete
• The Plan ID format may not match system requirements
• There may be a data integrity issue in the source document
• System may require manual intervention for this specific case

NEXT STEPS:
Please contact our support team with the following information:

┌──────────────────────────────────────────────────────────┐
│ Tracking ID: {item['id']}
│ Original Plan ID: {original_plan_id}
│ Customer Name: {name}
│ Submission Date: {item.get('created_at')}
│ Total Retry Attempts: {len(retry_status['attempts'])}
│
│ All Attempted Plan IDs:
{attempt_history}
└──────────────────────────────────────────────────────────┘

Our team will investigate and contact you within 24 hours.

IMPORTANT: Please DO NOT resubmit this request. Our team is already 
reviewing your case and will reach out to you directly.

Best regards,
JushQuant Associates - Automated Plan Setup System
"""
        
        try:
            recipient = data.get('_requester_email', 'prajush01@gmail.com')
            
            self.outlook.send_email(
                to=recipient,
                subject=f"URGENT: Plan Setup Failed After {len(retry_status['attempts'])} Attempts",
                body=email_body
            )
            logger.info(f"✅ Escalation email sent to {recipient}")
        except Exception as e:
            logger.error(f"❌ Failed to send escalation email: {str(e)}")
    
    def send_duplicate_submission_email(self, plan_id: str, registry_entry: Dict):
        """
        NEW: Send informational email when duplicate Plan ID is detected
        
        Args:
            plan_id: The duplicate Plan ID
            registry_entry: Registry entry showing previous attempts
        """
        requester_email = registry_entry.get('requester_email', 'prajush01@gmail.com')
        
        # Build attempt history
        attempt_history = ""
        for idx, attempt in enumerate(registry_entry['attempts'], 1):
            attempt_history += f"Attempt {idx}: Plan ID '{attempt['plan_id']}' → Failed (Plan ID Already Exists)\n"
        
        email_body = f"""Dear Customer,

We received a new submission for Plan ID: {plan_id}

However, our system shows that this Plan ID was already processed and escalated 
after multiple retry attempts.

PREVIOUS SUBMISSION DETAILS:
┌──────────────────────────────────────────────────────────┐
│ Original Plan ID: {plan_id}
│ First Submitted: {registry_entry.get('first_seen', 'Unknown')}
│ Status: ESCALATED (after {registry_entry['retry_count']} failed attempts)
│ Last Updated: {registry_entry.get('last_updated', 'Unknown')}
│
│ Previous Retry Attempts:
│ {attempt_history}
└──────────────────────────────────────────────────────────┘

WHAT THIS MEANS:
• Your original submission with this Plan ID has already been escalated to our 
  support team for manual review
• We are NOT reprocessing this submission to avoid duplicate work
• Our team is already investigating the issue

WHAT YOU SHOULD DO:
1. If you haven't heard from our support team, please contact them directly 
   with reference to Plan ID: {plan_id}
2. If this is a NEW request (not related to the previous submission), please 
   use a DIFFERENT Plan ID
3. Do not resubmit with the same Plan ID

CONTACT SUPPORT:
Please reference Plan ID {plan_id} and mention that it was previously escalated.

Thank you for your understanding.

Best regards,
JushQuant Associates - Automated Plan Setup System
"""
        
        try:
            self.outlook.send_email(
                to=requester_email,
                subject=f"Plan Setup - Duplicate Submission Detected ({plan_id})",
                body=email_body
            )
            logger.info(f"✅ Duplicate submission notification sent to {requester_email}")
        except Exception as e:
            logger.error(f"❌ Failed to send duplicate submission email: {str(e)}")
    
    def _send_data_error_email(self, item: Dict[str, Any]):
        """Send email for data validation errors"""
        data = item['data']
        name = data.get('name', 'Customer')
        exception = item.get('exception_reason', 'Unknown error')
        
        email_body = f"""Dear {name},

Your plan setup submission could not be processed due to a data validation error.

ISSUE DETECTED:
┌────────────────────────────────────────────────┐
│ ⚠️  {exception}                                 │
└────────────────────────────────────────────────┘

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
            logger.info(f"✅ Data error email sent to {recipient}")
        except Exception as e:
            logger.error(f"❌ Failed to send data error email: {str(e)}")
    
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
        logger.info(f"📋 Retry Registry: {RETRY_REGISTRY_PATH}")
        logger.info(f"{'='*80}\n")
        logger.info("Press Ctrl+C to stop\n")
        
        try:
            while True:
                self.process_exceptions()
                
                logger.info(f"💤 Waiting {poll_interval} seconds before next check...\n")
                time.sleep(poll_interval)
                    
        except KeyboardInterrupt:
            logger.info("\nℹ️  Exception Handler stopped by user")
        except Exception as e:
            logger.error(f"\n❌ Exception Handler error: {str(e)}")
            raise

# Load environment
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

email_address = os.getenv('EMAIL_ADDRESS')
app_password = os.getenv('APP_PASSWORD')

def main():
    """Main entry point for Exception Handler"""
    
    from agents.requestor_interaction_agent import RequestorInteractionAgent
    
    interaction_agent = RequestorInteractionAgent(None)
    queue = QueueManager(QUEUE_DATABASE)

    handler = BPExceptionHandler(queue, interaction_agent, outlook_connector=None)
    handler.run_continuous(poll_interval=10)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [AGENT 5] - %(message)s',
        handlers=[
            logging.FileHandler(LOG_DIR / "bp_exception_handler.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    main()