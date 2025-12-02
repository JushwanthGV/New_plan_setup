import os 
from langgraph.graph import StateGraph, END
from typing import TypedDict, Any, List
import logging

logger = logging.getLogger(__name__)

class EmailWorkflowState(TypedDict):
    """Enhanced state for the complete email processing workflow"""
    emails_found: List[dict]
    attachments_downloaded: List[str]
    validation_results: List[dict]
    interaction_results: List[dict]
    pending_requests_created: List[str]
    blueprism_submissions: List[dict]
    blueprism_success_count: int
    blueprism_failed_count: int
    responses_sent: List[dict]
    jsons_saved: List[str]
    status: str
    error: str | None
    current_email: dict | None

class EmailProcessingWorkflow:
    """
    Complete LangGraph workflow matching the Agentic AI Workflow diagram
    Includes: Agent 1 (Monitor), Agent 2 (Validate), Agent 3 (Interact), Agent 4 (Export)
    """

    def __init__(self, email_monitor_agent, document_validator_agent, 
                 requestor_interaction_agent, data_export_agent, 
                 document_parser):

        self.email_agent = email_monitor_agent
        self.validator_agent = document_validator_agent
        self.interaction_agent = requestor_interaction_agent
        self.export_agent = data_export_agent
        self.parser = document_parser
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build LangGraph state graph"""
        workflow = StateGraph(EmailWorkflowState)

        workflow.add_node("agent1_monitor_emails", self._agent1_monitor_emails)
        workflow.add_node("agent2_validate_documents", self._agent2_validate_documents)
        workflow.add_node("agent3_interact_requestor", self._agent3_interact_requestor)
        workflow.add_node("agent4_export_data", self._agent4_export_data)
        workflow.add_node("report_results", self._report_results)

        workflow.set_entry_point("agent1_monitor_emails")

        workflow.add_edge("agent1_monitor_emails", "agent2_validate_documents")
        workflow.add_edge("agent2_validate_documents", "agent3_interact_requestor")
        workflow.add_edge("agent3_interact_requestor", "agent4_export_data")
        workflow.add_edge("agent4_export_data", "report_results")
        workflow.add_edge("report_results", END)

        return workflow.compile()

    # -------------------------------------------------------------------------
    # AGENT 1 — EMAIL MONITORING
    # -------------------------------------------------------------------------
    def _agent1_monitor_emails(self, state: EmailWorkflowState) -> EmailWorkflowState:
        logger.info("="*80)
        logger.info("AGENT 1: EMAIL MONITORING - New Plan to Digital Format")
        logger.info("="*80)

        try:
            emails = self.email_agent.outlook.get_unread_emails(
                sender=self.email_agent.sender,
                subject=self.email_agent.subject,
                today_only=True
            )

            state['emails_found'] = []
            state['attachments_downloaded'] = []

            if not emails:
                logger.info("✗ No new plan setup emails found")
                state['status'] = 'no_emails'
                return state

            logger.info(f"✓ Found {len(emails)} new plan setup email(s)")

            for email_msg in emails:
                email_info = self.email_agent.outlook.get_email_info(email_msg)

                if self.email_agent.outlook.has_attachments(email_msg):

                    downloaded = self.email_agent.outlook.download_attachments(
                        email_msg,
                        self.email_agent.download_path
                    )

                    state['emails_found'].append({
                        'email_message': email_msg,
                        'sender': email_info['from'],
                        'subject': email_info['subject'],
                        'attachments': downloaded
                    })
                    state['attachments_downloaded'].extend(downloaded)

                    logger.info(f"✓ Downloaded {len(downloaded)} document(s) from {email_info['from']}")

                else:
                    reply_body = self.email_agent._generate_no_attachment_reply(email_msg)
                    self.email_agent.outlook.reply_to_email(email_msg, reply_body, mark_as_read=True)
                    logger.info(f"✗ No attachments — sent notification to {email_info['from']}")

            state['status'] = 'success' if state['attachments_downloaded'] else 'no_attachments'

        except Exception as e:
            logger.error(f"✗ Error in Agent 1 (Email Monitoring): {str(e)}")
            state['status'] = 'error'
            state['error'] = str(e)

        return state

    # -------------------------------------------------------------------------
    # AGENT 2 — DOCUMENT VALIDATION
    # -------------------------------------------------------------------------
    def _agent2_validate_documents(self, state: EmailWorkflowState) -> EmailWorkflowState:
        logger.info("="*80)
        logger.info("AGENT 2: DOCUMENT VALIDATION - Extract & Validate Required Info")
        logger.info("="*80)

        if not state.get('attachments_downloaded'):
            logger.info("✗ No attachments to validate")
            return state

        state['validation_results'] = []

        try:
            for attachment_path in state['attachments_downloaded']:
                logger.info(f"Processing: {attachment_path}")

                document_text = self.parser.parse_document(attachment_path)

                if not document_text:
                    logger.warning(f"⚠ Could not extract text from: {attachment_path}")
                    state['validation_results'].append({
                        'all_fields_present': False,
                        'extracted_data': {},
                        'missing_fields': self.validator_agent.mandatory_fields,
                        'filename': attachment_path,
                        'error_type': 'cannot_read_document',
                        'error_message': 'Unable to extract text'
                    })
                    continue

                logger.info(f"✓ Extracted {len(document_text)} characters of text")

                validation_result = self.validator_agent.validate_and_extract(
                    document_text,
                    attachment_path
                )

                state['validation_results'].append(validation_result)

                if validation_result['all_fields_present']:
                    logger.info(f"✓ Validation PASSED: {attachment_path}")
                else:
                    logger.warning(f"✗ Validation FAILED: {attachment_path}")
                    logger.warning(f"   Missing fields: {', '.join(validation_result['missing_fields'])}")

        except Exception as e:
            logger.error(f"✗ Error in Agent 2 (Document Validation): {str(e)}")
            state['error'] = str(e)

        return state

    # -------------------------------------------------------------------------
    # AGENT 3 — REQUESTOR INTERACTION
    # -------------------------------------------------------------------------
    def _agent3_interact_requestor(self, state: EmailWorkflowState) -> EmailWorkflowState:
        logger.info("="*80)
        logger.info("AGENT 3: REQUESTOR INTERACTION - Handle Missing Info & Follow-ups")
        logger.info("="*80)

        if not state.get('validation_results'):
            logger.info("✗ No validation results to handle")
            return state

        state['interaction_results'] = []
        state['pending_requests_created'] = []
        state['responses_sent'] = []
        state['jsons_saved'] = []

        try:
            for email_data in state.get('emails_found', []):
                sender_email = email_data['sender']
                email_message = email_data['email_message']

                for attachment_path in email_data.get('attachments', []):
                    validation = next(
                        (v for v in state['validation_results'] if v['filename'] == attachment_path),
                        None
                    )
                    if not validation:
                        continue

                    interaction_result = self.interaction_agent.handle_validation_result(
                        validation,
                        sender_email,
                        email_message
                    )

                    state['interaction_results'].append(interaction_result)

                    if interaction_result.get('email_sent'):
                        state['responses_sent'].append({'recipient': sender_email})

                    if interaction_result.get('request_tracked'):
                        tracking_id = interaction_result.get('tracking_id')
                        if tracking_id:
                            state['pending_requests_created'].append(tracking_id)

                    if validation['all_fields_present']:
                        json_path = self.validator_agent.save_validated_data(validation)
                        if json_path:
                            state['jsons_saved'].append(json_path)
                            logger.info(f"✓ Saved validated data: {json_path}")

                    else:
                        try:
                            if os.path.exists(attachment_path):
                                os.remove(attachment_path)
                                logger.info(f"🗑 Deleted invalid document: {attachment_path}")
                            else:
                                logger.warning(f"⚠ File not found for deletion: {attachment_path}")
                        except Exception as del_err:
                            logger.error(f"⚠ Failed to delete invalid document: {str(del_err)}")

                    self.email_agent.outlook.mark_as_read(email_message)

            logger.info(f"✓ Processed {len(state['interaction_results'])} interaction(s)")
            logger.info(f"✓ Sent {len(state['responses_sent'])} notification(s)")
            logger.info(f"✓ Created {len(state['pending_requests_created'])} pending request(s)")

        except Exception as e:
            logger.error(f"✗ Error in Agent 3 (Requestor Interaction): {str(e)}")
            state['error'] = str(e)

        return state
    # -------------------------------------------------------------------------
    # AGENT 4 — DATA EXPORT
    # -------------------------------------------------------------------------
    def _agent4_export_data(self, state: EmailWorkflowState) -> EmailWorkflowState:
        logger.info("="*80)
        logger.info("AGENT 4: DATA EXPORT - Convert to JSON & Save to Network Folder")
        logger.info("="*80)

        if not state.get('validation_results'):
            logger.info("✗ No validation results to export")
            state['blueprism_submissions'] = []
            state['blueprism_success_count'] = 0
            state['blueprism_failed_count'] = 0
            return state
        
        try:
            export_results = self.export_agent.process_validated_data(
                state['validation_results']
            )

            state['blueprism_submissions'] = export_results.get('exports', [])
            state['blueprism_success_count'] = export_results.get('successful_exports', 0)
            state['blueprism_failed_count'] = export_results.get('failed_exports', 0)

            if state['blueprism_success_count'] > 0:
                logger.info(f"✓ Successfully exported {state['blueprism_success_count']} file(s) to network folder")

            if state['blueprism_failed_count'] > 0:
                logger.warning(f"⚠ Failed to export {state['blueprism_failed_count']} file(s)")

            logger.info("\nExport Details:")
            logger.info("-" * 80)

            for export in state['blueprism_submissions']:
                status_icon = "✓" if export.get('success') else "✗"
                logger.info(f"{status_icon} {export.get('filename')}")

                if export.get('export_filepath'):
                    logger.info(f"   Saved to: {export.get('export_filepath')}")

                if export.get('error'):
                    logger.info(f"   Error: {export.get('error')}")

        except Exception as e:
            logger.error(f"✗ Error in Agent 4 (Data Export): {str(e)}")
            state['error'] = str(e)
            state['blueprism_submissions'] = []
            state['blueprism_success_count'] = 0
            state['blueprism_failed_count'] = 0
        
        return state

    # -------------------------------------------------------------------------
    # FINAL SUMMARY REPORT
    # -------------------------------------------------------------------------
    def _report_results(self, state: EmailWorkflowState) -> EmailWorkflowState:
        logger.info("="*80)
        logger.info("WORKFLOW EXECUTION SUMMARY")
        logger.info("="*80)

        logger.info("\n📧 AGENT 1 - Email Monitoring:")
        logger.info(f"   • Emails processed: {len(state.get('emails_found', []))}")
        logger.info(f"   • Attachments downloaded: {len(state.get('attachments_downloaded', []))}")

        logger.info("\n📄 AGENT 2 - Document Validation:")
        logger.info(f"   • Documents validated: {len(state.get('validation_results', []))}")
        valid_count = sum(1 for v in state.get('validation_results', []) if v.get('all_fields_present'))
        invalid_count = len(state.get('validation_results', [])) - valid_count
        logger.info(f"   • Valid documents: {valid_count}")
        logger.info(f"   • Invalid/incomplete documents: {invalid_count}")

        logger.info("\n💬 AGENT 3 - Requestor Interaction:")
        logger.info(f"   • Interactions processed: {len(state.get('interaction_results', []))}")
        logger.info(f"   • Notification emails sent: {len(state.get('responses_sent', []))}")
        logger.info(f"   • Pending requests created: {len(state.get('pending_requests_created', []))}")
        logger.info(f"   • JSON files saved: {len(state.get('jsons_saved', []))}")

        logger.info("\n📤 AGENT 4 - Data Export:")
        logger.info(f"   • Total exports: {len(state.get('blueprism_submissions', []))}")
        logger.info(f"   • Successful: {state.get('blueprism_success_count', 0)}")
        logger.info(f"   • Failed: {state.get('blueprism_failed_count', 0)}")

        if state.get('blueprism_success_count', 0) > 0:
            logger.info(f"   • Export path: {self.export_agent.exporter.export_path}")

        if state.get('error'):
            logger.error(f"\n✗ Errors encountered: {state['error']}")

        logger.info("="*80)
        return state

    # -------------------------------------------------------------------------
    # WORKFLOW RUNNER
    # -------------------------------------------------------------------------
    def run(self) -> dict:
        logger.info("="*80)
        logger.info("STARTING AGENTIC AI WORKFLOW - NEW PLAN SETUP PROCESS")
        logger.info("="*80)

        initial_state = {
            'emails_found': [],
            'attachments_downloaded': [],
            'validation_results': [],
            'interaction_results': [],
            'pending_requests_created': [],
            'blueprism_submissions': [],
            'blueprism_success_count': 0,
            'blueprism_failed_count': 0,
            'responses_sent': [],
            'jsons_saved': [],
            'status': 'pending',
            'error': None,
            'current_email': None
        }

        final_state = self.graph.invoke(initial_state)

        logger.info("\n" + "="*80)
        logger.info("WORKFLOW EXECUTION COMPLETED")
        logger.info("="*80)

        return final_state
