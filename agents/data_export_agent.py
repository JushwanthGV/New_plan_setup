import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DataExportAgent:
    """
    Agent 4 - Responsible for converting validated data to JSON 
    and saving to network shared folder
    UPDATED: Plan ID must come from PDF - NO auto-generation here
    """
    
    def __init__(self, data_exporter, log_exports: bool = True, log_path: str = None):
        """
        Initialize Data Export Agent
        
        Args:
            data_exporter: Instance of DataExporter
            log_exports: Whether to log all exports
            log_path: Path to save export logs (optional)
        """
        self.exporter = data_exporter
        self.log_exports = log_exports
        self.log_path = log_path
        logger.info("Data Export Agent initialized (Agent 4)")
    
    def process_validated_data(self, validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process all validated data and export to network folder
        
        Args:
            validation_results: List of validation result dictionaries
            
        Returns:
            Dictionary with processing results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_processed': 0,
            'successful_exports': 0,
            'failed_exports': 0,
            'exports': []
        }
        
        try:
            # Filter only successfully validated documents
            valid_documents = [
                doc for doc in validation_results 
                if doc.get('all_fields_present', False)
            ]
            
            if not valid_documents:
                logger.info("⊘ No validated documents to export")
                return results
            
            logger.info(f"Processing {len(valid_documents)} validated document(s) for export")
            
            # Process each validated document
            for doc in valid_documents:
                export_result = self._export_single_document(doc)
                results['exports'].append(export_result)
                results['total_processed'] += 1
                
                if export_result.get('success'):
                    results['successful_exports'] += 1
                else:
                    results['failed_exports'] += 1
            
            logger.info(f"Export processing complete - Success: {results['successful_exports']}, Failed: {results['failed_exports']}")
            
        except Exception as e:
            logger.error(f"Error processing validated data: {str(e)}")
            results['error'] = str(e)
        
        return results
    
    def _export_single_document(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export a single validated document to JSON in network folder
        
        Args:
            validated_data: Validated document data
            
        Returns:
            Export result
        """
        filename = validated_data.get('filename', validated_data.get('source_document', 'unknown'))
        
        try:
            logger.info(f"Exporting document: {filename}")
            
            # Step 1: Convert to JSON format
            logger.info("Step 1: Converting data to JSON format...")
            json_data = self.exporter.convert_to_json_format(validated_data)
            
            # Step 2: Save to network folder
            logger.info("Step 2: Saving to network shared folder...")
            response = self.exporter.save_to_network_folder(json_data)
            
            # Step 3: Log export if enabled
            if self.log_exports and self.log_path:
                self.exporter.create_export_log(json_data, response, self.log_path)
            
            # Prepare result
            result = {
                'filename': filename,
                'success': response.get('success', False),
                'export_id': json_data.get('export_id'),
                'export_filepath': response.get('filepath'),
                'status': response.get('status', 'unknown'),
                'message': response.get('message', ''),
                'timestamp': datetime.now().isoformat()
            }
            
            if response.get('success'):
                logger.info(f"✅ Successfully exported to network folder: {filename}")
                logger.info(f"   File: {response.get('filename')}")
                logger.info(f"   Path: {response.get('filepath')}")
                try:
                    # Get Plan ID from validated data (must be present since validation passed)
                    plan_id = validated_data.get('extracted_data', {}).get('plan_id')
                    
                    if not plan_id:
                        logger.error("❌ Plan ID missing even after validation - this should not happen!")
                        return result
                    
                    logger.info(f"📋 Using Plan ID from PDF: {plan_id}")
                    self.add_to_bp_queue(validated_data, response.get('filename', filename), plan_id)
                except Exception as e:
                    logger.error(f"Failed to add to BP queue: {e}")
            else:
                logger.error(f"❌ Failed to export: {filename} - {response.get('error')}")
                result['error'] = response.get('error')
                result['error_details'] = response.get('error_details')
            
            return result
            
        except Exception as e:
            logger.error(f"Error exporting document {filename}: {str(e)}")
            return {
                'filename': filename,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def retry_failed_export(self, failed_result: Dict[str, Any], 
                           validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retry a failed export
        
        Args:
            failed_result: Previous failed export result
            validated_data: Original validated data
            
        Returns:
            Retry result
        """
        logger.info(f"Retrying export for: {failed_result.get('filename')}")
        return self._export_single_document(validated_data)
    
    def get_export_summary(self, results: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of exports
        
        Args:
            results: Processing results dictionary
            
        Returns:
            Summary string
        """
        summary = f"""
Data Export Summary (Agent 4)
{'='*80}
Total Documents Processed: {results['total_processed']}
Successful Exports: {results['successful_exports']}
Failed Exports: {results['failed_exports']}
Export Path: {self.exporter.export_path}
{'='*80}
"""
        
        if results.get('exports'):
            summary += "\nDetailed Results:\n"
            for idx, exp in enumerate(results['exports'], 1):
                status_icon = "✅" if exp.get('success') else "❌"
                summary += f"{idx}. {status_icon} {exp.get('filename')} - {exp.get('status', 'unknown')}\n"
                if exp.get('export_filepath'):
                    summary += f"   Saved to: {exp.get('export_filepath')}\n"
                if exp.get('error'):
                    summary += f"   Error: {exp.get('error')}\n"
        
        return summary
    
    def validate_export_path(self) -> bool:
        """
        Validate that export path is accessible
        
        Returns:
            True if path is accessible
        """
        return self.exporter.validate_export_path()
    
    def get_network_folder_summary(self) -> Dict[str, Any]:
        """
        Get summary of files in network folder
        
        Returns:
            Summary dictionary
        """
        return self.exporter.get_export_summary()
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        folder_summary = self.get_network_folder_summary()
        
        return {
            'agent': 'DataExportAgent',
            'export_path': str(self.exporter.export_path),
            'export_path_accessible': folder_summary.get('accessible', False),
            'total_exported_files': folder_summary.get('total_files', 0),
            'log_exports': self.log_exports,
            'status': 'active'
        }
    
    def add_to_bp_queue(self, validated_data: Dict[str, Any], json_filename: str, plan_id: str) -> bool:
        """
        Add validated data to Blue Prism work queue
        UPDATED: Plan ID is now REQUIRED (no auto-generation)
        
        Args:
            validated_data: Validated plan data
            json_filename: Source JSON filename
            plan_id: Plan ID from PDF (REQUIRED - must be provided)
            
        Returns:
            True if successfully added to queue
        """
        try:
            import sys
            from pathlib import Path
            
            
            # Get project root
            project_root = Path(__file__).parent.parent
            
            # Add mock_queue to path
            mock_queue_path = project_root / 'mock_queue'
            if str(mock_queue_path) not in sys.path:
                sys.path.append(str(mock_queue_path))
            
            from mock_queue.queue_manager import QueueManager
            from mock_queue.config import QUEUE_DATABASE
            
            # Ensure queue database path is correct
            if isinstance(QUEUE_DATABASE, Path):
                queue_db = str(QUEUE_DATABASE)
            else:
                queue_db = str(project_root / "data" / "queue.json")
            
            # Ensure queue directory exists
            Path(queue_db).parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize queue manager
            queue = QueueManager(queue_db)
            
            # Add source document info
            validated_data['_source_document'] = json_filename
            
            # Use the Plan ID from PDF (REQUIRED)
            if not plan_id:
                logger.error("❌ Cannot add to queue - Plan ID is missing!")
                return False
            
            logger.info(f"📋 Adding to queue with Plan ID from PDF: {plan_id}")
            item_id = queue.add_item(validated_data, plan_id=plan_id)
            
            logger.info(f"✅ Added to BP queue: {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to add to BP queue: {str(e)}")
            logger.error(f"   Queue path attempted: {queue_db if 'queue_db' in locals() else 'unknown'}")
            return False