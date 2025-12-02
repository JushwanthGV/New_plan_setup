import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class OutlookConnector:
    """Connector for email using IMAP/SMTP (works with Gmail and Outlook)"""
    
    # IMAP/SMTP server configurations
    SERVERS = {
        'outlook': {
            'imap_server': 'outlook.office365.com',
            'imap_port': 993,
            'smtp_server': 'smtp.office365.com',
            'smtp_port': 587
        },
        'gmail': {
            'imap_server': 'imap.gmail.com',
            'imap_port': 993,
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587
        }
    }
    
    def __init__(self, email_address: str, app_password: str, provider: str = 'outlook'):
        """
        Initialize connector with IMAP/SMTP
        
        Args:
            email_address: Your email address
            app_password: App-specific password (not your regular password)
            provider: 'outlook' or 'gmail'
        """
        self.email_address = email_address
        self.app_password = app_password
        self.provider = provider.lower()
        
        if self.provider not in self.SERVERS:
            raise ValueError(f"Provider must be 'outlook' or 'gmail', got: {provider}")
        
        self.config = self.SERVERS[self.provider]
        
        # Test connection
        self._test_connection()
        logger.info(f"Successfully connected to {provider} IMAP/SMTP for: {email_address}")
    
    def _test_connection(self):
        """Test IMAP connection"""
        try:
            mail = imaplib.IMAP4_SSL(self.config['imap_server'], self.config['imap_port'])
            mail.login(self.email_address, self.app_password)
            mail.logout()
        except Exception as e:
            raise Exception(f"IMAP connection failed: {str(e)}")
    
    def _connect_imap(self):
        """Create and return IMAP connection"""
        mail = imaplib.IMAP4_SSL(self.config['imap_server'], self.config['imap_port'])
        mail.login(self.email_address, self.app_password)
        return mail
    
    def get_unread_emails(self, sender: str = None, subject: str = None, today_only: bool = True):
        """
        Fetch unread emails with optional filters
        
        Args:
            sender: Filter by sender email
            subject: Filter by subject line (partial match)
            today_only: Only get emails from today
            
        Returns:
            List of email message objects
        """
        mail = self._connect_imap()
        mail.select('INBOX')
        
        # Build search criteria
        search_criteria = ['UNSEEN']  # Unread emails
        
        if today_only:
            today = datetime.now().strftime("%d-%b-%Y")
            search_criteria.append(f'SINCE {today}')
        
        if sender:
            search_criteria.append(f'FROM "{sender}"')
        
        if subject:
            search_criteria.append(f'SUBJECT "{subject}"')
        
        # Search for emails
        search_string = ' '.join(search_criteria)
        status, messages = mail.search(None, search_string)
        
        email_ids = messages[0].split()
        emails = []
        
        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)
                
                # Store email_id for later operations
                email_message.email_id = email_id
                emails.append(email_message)
            except Exception as e:
                logger.error(f"Error fetching email {email_id}: {str(e)}")
        
        mail.close()
        mail.logout()
        
        logger.info(f"Found {len(emails)} unread emails matching criteria")
        return emails
    
    def download_attachments(self, email_message, download_path: str):
        """
        Download all attachments from an email
        
        Args:
            email_message: Email message object
            download_path: Path to save attachments
            
        Returns:
            List of downloaded file paths
        """
        downloaded_files = []
        
        # Create download directory if it doesn't exist
        Path(download_path).mkdir(parents=True, exist_ok=True)
        
        for part in email_message.walk():
            # Check if part has attachment
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    # Generate safe filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_filename = f"{timestamp}_{filename}"
                    filepath = os.path.join(download_path, safe_filename)
                    
                    # Save attachment
                    with open(filepath, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    
                    downloaded_files.append(filepath)
                    logger.info(f"Downloaded attachment: {safe_filename}")
        
        if not downloaded_files:
            logger.info("No attachments found in email")
        
        return downloaded_files
    
    def has_attachments(self, email_message):
        """Check if email has attachments"""
        for part in email_message.walk():
            if part.get_content_disposition() == 'attachment':
                return True
        return False
    
    def reply_to_email(self, email_message, body: str, mark_as_read: bool = True):
        """
        Reply to an email
        
        Args:
            email_message: The email message to reply to
            body: Body text of the reply
            mark_as_read: Whether to mark the original email as read
        """
        try:
            # Get original sender
            from_addr = email.utils.parseaddr(email_message['From'])[1]
            subject = email_message['Subject']
            message_id = email_message['Message-ID']
            
            # Create reply message
            reply = MIMEMultipart()
            reply['From'] = self.email_address
            reply['To'] = from_addr
            reply['Subject'] = f"Re: {subject}" if not subject.startswith('Re:') else subject
            reply['In-Reply-To'] = message_id
            reply['References'] = message_id
            
            # Add body
            reply.attach(MIMEText(body, 'plain'))
            
            # Send via SMTP
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_address, self.app_password)
                server.send_message(reply)
            
            logger.info(f"Sent reply to: {from_addr}")
            
            # Mark as read if requested
            if mark_as_read:
                self.mark_as_read(email_message)
                
        except Exception as e:
            logger.error(f"Error sending reply: {str(e)}")
            raise
    
    def mark_as_read(self, email_message):
        """Mark an email as read"""
        try:
            mail = self._connect_imap()
            mail.select('INBOX')
            
            # Mark as seen
            mail.store(email_message.email_id, '+FLAGS', '\\Seen')
            
            mail.close()
            mail.logout()
            
            logger.info(f"Marked email as read")
        except Exception as e:
            logger.error(f"Error marking email as read: {str(e)}")
    
    def send_email(self, to: str, subject: str, body: str):
        """
        Send a new email
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = to
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send via SMTP
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_address, self.app_password)
                server.send_message(msg)
            
            logger.info(f"Sent email to: {to}")
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            raise
    
    def get_email_info(self, email_message):
        """Get basic info from email message"""
        from_addr = email.utils.parseaddr(email_message['From'])[1]
        subject = email_message['Subject']
        date = email_message['Date']
        
        return {
            'from': from_addr,
            'subject': subject,
            'date': date
        }