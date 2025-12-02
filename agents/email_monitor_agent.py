import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailMonitorAgent:
    """
    Agent responsible for monitoring emails and processing attachments
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
        logger.info(f"Email Monitor Agent initialized - Monitoring sender: {self.sender}, subject: {self.subject}")
    
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