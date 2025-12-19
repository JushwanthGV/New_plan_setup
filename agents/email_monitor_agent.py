import logging
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class EmailMonitorAgent:
    """
    Agent responsible for monitoring emails and processing attachments
    UPDATED: Now checks for duplicate submissions against retry registry
    """
    
    def __init__(self, outlook_connector, monitor_config: Dict[str, Any]):
        """
        Initialize the Email Monitor Agent
        
        Args:
            outlook_connector: Instance of OutlookConnector
            monitor_config: Configuration dict with keys:
                - sender: Email sender to monitor
                - subject: Subject line to filter
                - download_path: Path to save attachments
        """
        self.outlook = outlook_connector
        self.sender = monitor_config.get('sender')
        self.subject = monitor_config.get('subject')
        self.download_path = monitor_config.get('download_path')
        
        # NEW: Path to retry registry for duplicate detection
        self.retry_registry_path = Path(__file__).parent.parent / "data" / "retry_registry.json"
        
        logger.info(f"Email Monitor Agent initialized - Monitoring sender: {self.sender}, subject: {self.subject}")
    
    def _load_retry_registry(self) -> Dict:
        """NEW: Load retry registry to check for duplicates"""
        import json
        try:
            if self.retry_registry_path.exists():
                with open(self.retry_registry_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading retry registry: {str(e)}")
            return {}
    
    def _check_duplicate_plan_id(self, plan_id: str, requester_email: str) -> bool:
        """
        NEW: Check if Plan ID was already escalated
        
        Args:
            plan_id: Plan ID extracted from document
            requester_email: Email of requestor
            
        Returns:
            True if duplicate and already escalated
        """
        registry = self._load_retry_registry()
        
        if plan_id in registry:
            entry = registry[plan_id]
            if entry.get('status') == 'ESCALATED':
                logger.warning(f"🚫 DUPLICATE PLAN ID DETECTED: {plan_id}")
                logger.warning(f"   Status: ESCALATED (already processed)")
                logger.warning(f"   Retry Count: {entry.get('retry_count', 0)}")
                logger.warning(f"   First Seen: {entry.get('first_seen', 'Unknown')}")
                return True
        
        return False
    
    def check_emails(self) -> Dict[str, Any]:
        """
        Main method to check for new emails and process them
        
        Returns:
            Dictionary with processing results
        """
        logger.info("Starting email check...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'emails_processed': 0,
            'attachments_downloaded': 0,
            'replies_sent': 0,
            'duplicates_detected': 0,  # NEW: Track duplicates
            'errors': []
        }
        
        try:
            # Get unread emails matching criteria
            emails = self.outlook.get_unread_emails(
                sender=self.sender,
                subject=self.subject,
                today_only=True
            )
            
            if not emails:
                logger.info("No new emails found matching criteria")
                return results
            
            # Process each email
            for email in emails:
                try:
                    self._process_email(email, results)
                except Exception as e:
                    error_msg = f"Error processing email '{email.subject}': {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            logger.info(f"Email check complete. Processed {results['emails_processed']} emails")
            
            # NEW: Log duplicate detections
            if results['duplicates_detected'] > 0:
                logger.info(f"   Duplicates detected and handled: {results['duplicates_detected']}")
            
        except Exception as e:
            error_msg = f"Error during email check: {str(e)}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def _process_email(self, email_message, results: Dict):
        """
        Process a single email
        
        Args:
            email_message: Email message object from imaplib
            results: Results dictionary to update
        """
        email_info = self.outlook.get_email_info(email_message)
        
        logger.info(f"Processing email from {email_info['from']}: {email_info['subject']}")
        
        # Check if email has attachments
        if self.outlook.has_attachments(email_message):
            logger.info(f"Email has attachments")
            
            # Download attachments
            downloaded_files = self.outlook.download_attachments(email_message, self.download_path)
            results['attachments_downloaded'] += len(downloaded_files)
            
            # Mark email as read
            self.outlook.mark_as_read(email_message)
            
            logger.info(f"Successfully downloaded {len(downloaded_files)} attachment(s)")
            
        else:
            # No attachments found - send reply
            logger.info("No attachments found in email")
            
            reply_body = self._generate_no_attachment_reply(email_message)
            self.outlook.reply_to_email(email_message, reply_body, mark_as_read=True)
            results['replies_sent'] += 1
            
            logger.info("Sent 'no attachments' reply")
        
        results['emails_processed'] += 1
    
    def _generate_no_attachment_reply(self, email_message) -> str:
        """
        Generate reply message for emails without attachments
        
        Args:
            email_message: Email message object
            
        Returns:
            Reply message body
        """
        subject = email_message.get('Subject', 'your email')
        return f"""Hello,

Thank you for your email regarding "{subject}".

We noticed that your email did not contain any attachments. If you intended to send attachments, please resend the email with the files attached.

If you have any questions, please feel free to reach out.

Best regards,
Email Monitoring System
"""
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current agent status
        
        Returns:
            Status dictionary
        """
        return {
            'agent': 'EmailMonitorAgent',
            'monitoring_sender': self.sender,
            'monitoring_subject': self.subject,
            'download_path': self.download_path,
            'status': 'active'
        }