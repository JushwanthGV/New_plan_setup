import logging
from typing import Dict, List, Any
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class RequestorInteractionAgent:
    """
    Agent 3 - Enhanced interaction with requestor for missing information
    Handles follow-ups, tracks pending requests, and manages email communication
    """
    
    def __init__(self, outlook_connector, tracking_path: str = "./data/pending_requests"):
        """
        Initialize Requestor Interaction Agent
        
        Args:
            outlook_connector: Instance of OutlookConnector for email communication
            tracking_path: Path to store pending request tracking data
        """
        self.outlook = outlook_connector
        self.tracking_path = tracking_path
        
        # Create tracking directory
        Path(tracking_path).mkdir(parents=True, exist_ok=True)
        
        logger.info("Requestor Interaction Agent initialized")
    
    def handle_validation_result(self, validation_result: Dict[str, Any], sender_email: str, 
                                 original_email_message=None) -> Dict[str, Any]:
        """
        Enhanced handling of validation results with detailed tracking
        
        Args:
            validation_result: Result from document validator
            sender_email: Email address to send response to
            original_email_message: Original email message object
            
        Returns:
            Dictionary with action taken
        """
        result = {
            'action': None,
            'email_sent': False,
            'request_tracked': False,
            'error': None
        }
        
        try:
            # Handle unreadable documents
            if validation_result.get('error_type') == 'cannot_read_document':
                logger.info(f"Document unreadable - sending notification to {sender_email}")
                
                email_body = self._generate_unreadable_document_email(validation_result)
                self._send_email_with_tracking(
                    sender_email, 
                    email_body, 
                    validation_result,
                    request_type='unreadable'
                )
                
                result['action'] = 'unreadable_document_notification_sent'
                result['email_sent'] = True
                result['request_tracked'] = True
            
           
            # Handle validation success
            elif validation_result['all_fields_present']:
                logger.info(f"✓ All mandatory fields present in document: {validation_result['filename']}")
                result['action'] = 'validation_successful'
                # NO EMAIL SENT - silent success
            
            # Handle missing fields
            else:
                logger.info(f"✗ Missing fields: {', '.join(validation_result['missing_fields'])}")
                
                email_body = self._generate_missing_fields_email(validation_result)
                tracking_id = self._send_email_with_tracking(
                    sender_email, 
                    email_body, 
                    validation_result,
                    request_type='missing_fields'
                )
                
                result['action'] = 'missing_fields_notification_sent'
                result['email_sent'] = True
                result['request_tracked'] = True
                result['tracking_id'] = tracking_id
                
        except Exception as e:
            logger.error(f"Error handling validation result: {str(e)}")
            result['error'] = str(e)
        
        return result
    
    def _send_email_with_tracking(self, recipient: str, body: str, 
                                  validation_result: Dict[str, Any], 
                                  request_type: str) -> str:
        """
        Send email and create tracking record
        
        Args:
            recipient: Email recipient
            body: Email body
            validation_result: Validation result data
            request_type: Type of request ('missing_fields', 'unreadable', etc.)
            
        Returns:
            Tracking ID
        """
        try:
            # Generate tracking ID
            tracking_id = f"REQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Add tracking ID to email
            tracked_body = f"[Reference: {tracking_id}]\n\n{body}"
            
            # Send email
            subject_map = {
                'missing_fields': "Document Validation - Missing Required Fields",
                'unreadable': "Document Processing - Unable to Read Document",
                'follow_up': "Document Processing - Follow-up Required"
            }
            
            self.outlook.send_email(
                to=recipient,
                subject=subject_map.get(request_type, "Document Processing Update"),
                body=tracked_body
            )
            
            # Create tracking record
            tracking_data = {
                'tracking_id': tracking_id,
                'recipient': recipient,
                'request_type': request_type,
                'sent_at': datetime.now().isoformat(),
                'status': 'pending_response',
                'validation_result': validation_result,
                'email_body': body,
                'follow_ups': [],
                'resolved': False
            }
            
            # Save tracking record
            self._save_tracking_record(tracking_id, tracking_data)
            
            logger.info(f"Sent tracked email to {recipient} - Tracking ID: {tracking_id}")
            
            return tracking_id
            
        except Exception as e:
            logger.error(f"Error sending tracked email: {str(e)}")
            raise
    
    def _save_tracking_record(self, tracking_id: str, data: Dict[str, Any]):
        """Save tracking record to file"""
        try:
            filepath = Path(self.tracking_path) / f"{tracking_id}.json"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved tracking record: {tracking_id}")
            
        except Exception as e:
            logger.error(f"Error saving tracking record: {str(e)}")
    
    def _generate_missing_fields_email(self, validation_result: Dict[str, Any]) -> str:
        """Generate professional email for missing fields"""
        missing_fields = validation_result.get('missing_fields', [])
        filename = Path(validation_result['filename']).name
        extracted_data = validation_result.get('extracted_data', {})
        
        # Get present fields (fields with non-empty values)
        present_fields = []
        for field in extracted_data.keys():
            value = extracted_data.get(field, "")
            if value and str(value).strip():
                present_fields.append(field)
        
        # Format missing fields
        if missing_fields:
            missing_list = "\n".join([
                f"   ❌ {field.replace('_', ' ').title()}"
                for field in missing_fields
            ])
        else:
            missing_list = "   None"
        
        # Format present fields
        if present_fields:
            present_list = "\n".join([
                f"   ✅ {field.replace('_', ' ').title()}: {extracted_data[field]}"
                for field in present_fields
            ])
        else:
            present_list = "   None"
        
        # Build checklist from all fields
        all_fields = list(set(missing_fields + present_fields))
        if all_fields:
            checklist = "\n".join([
                f"   {'✅' if field in present_fields else '❌'} {field.replace('_', ' ').title()}" +
                (f": {extracted_data.get(field, '')}" if field in present_fields else " - MISSING")
                for field in all_fields
            ])
        else:
            checklist = "   No fields extracted"
        
        email_body = f"""Dear Requestor,

Thank you for submitting your New Plan Setup document "{filename}".

Upon automated review, we found that the following mandatory information is MISSING:

{missing_list}

CURRENT STATUS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Information Received:
{present_list}

❌ Information Still Required:
{missing_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXT STEPS:
Please send a new email with a corrected document containing ALL required information, or provide the missing details listed above.

REQUIRED INFORMATION CHECKLIST:

{checklist}

Once we receive the complete information, your New Plan Setup will be processed automatically.

If you have any questions or need assistance, please contact us.

Best regards,
Suresh Babu G
Plan Setup Team

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is an automated message from our Agentic AI Workflow System.

For urgent matters, please contact your JushQuant Associate directly.
"""
        
        return email_body
    
    def _generate_unreadable_document_email(self, validation_result: Dict[str, Any]) -> str:
        """Generate email for unreadable documents"""
        filename = Path(validation_result['filename']).name
        missing_fields = validation_result.get('missing_fields', [])
        
        fields_required = ', '.join([f.replace('_', ' ').title() for f in missing_fields])
        
        return f"""Dear Requestor,

Thank you for submitting your document "{filename}".

ISSUE DETECTED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ We were unable to extract text content from your document.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

POSSIBLE CAUSES:
- Document is scanned but not OCR-processed
- Document is password-protected
- Document format is not supported
- Document is corrupted or damaged
- Image quality is too low for text extraction

RECOMMENDED ACTIONS:
1. If this is a scanned document, please ensure it has been OCR-processed
2. If password-protected, please send an unprotected version
3. Try converting to PDF format if using another format
4. Ensure the document is not corrupted
5. If scanned, re-scan at higher quality (300+ DPI recommended)

ALTERNATIVE:
If the document cannot be fixed, please provide the required information in one of these ways:
- Type the information directly in an email reply
- Fill out our digital form (if available)
- Contact your JushQuant Associate for manual processing

REQUIRED INFORMATION:
- {fields_required}

We apologize for any inconvenience. Once we receive a readable document or the information directly, we will process your New Plan Setup immediately.

Best regards,
Suresh Babu G
Plan Setup Team
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated message from our Agentic AI Workflow System.
"""
    
    def _generate_success_email(self, validation_result: Dict[str, Any]) -> str:
        """Generate success confirmation email"""
        filename = Path(validation_result['filename']).name
        extracted_data = validation_result.get('extracted_data', {})
        
        # Format extracted data
        data_summary = "\n".join([
            f"  ✅ {key.replace('_', ' ').title()}: {value}"
            for key, value in extracted_data.items()
            if value and str(value).strip()
        ])
        
        return f"""Dear Requestor,

✅ SUCCESS! Your document has been validated and accepted.

DOCUMENT: "{filename}"
STATUS: All required information received

INFORMATION EXTRACTED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{data_summary}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXT STEPS:
Your New Plan Setup is now being processed automatically. You will receive confirmation once the setup is complete.

Thank you for providing complete and accurate information!

Best regards,
Suresh Babu G
Plan Setup Team

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated confirmation from our Agentic AI Workflow System.
"""
    
    def _should_send_success_notification(self) -> bool:
        """Check if success notifications should be sent (configurable)"""
        return True
    
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending requests"""
        try:
            pending = []
            
            for filepath in Path(self.tracking_path).glob("*.json"):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if not data.get('resolved', False):
                        pending.append(data)
            
            return pending
            
        except Exception as e:
            logger.error(f"Error getting pending requests: {str(e)}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        pending_count = len(self.get_pending_requests())
        
        return {
            'agent': 'RequestorInteractionAgent',
            'pending_requests': pending_count,
            'tracking_path': self.tracking_path,
            'status': 'active'
        }