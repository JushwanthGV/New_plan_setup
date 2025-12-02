import logging
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)

class DataExporter:
    """
    Simple data exporter that converts validated data to JSON
    and saves to a network shared folder (no Blue Prism API calls)
    """
    
    def __init__(self, export_path: str):
        """
        Initialize Data Exporter
        
        Args:
            export_path: Path to network shared folder or local export folder
        """
        self.export_path = Path(export_path)
        
        # Create export directory if it doesn't exist
        try:
            self.export_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Data Exporter initialized - Export path: {export_path}")
        except Exception as e:
            logger.error(f"Failed to create export directory: {str(e)}")
            raise
    
    def convert_to_json_format(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert validated data to clean JSON format
        
        Args:
            validated_data: Dictionary with extracted and validated data
            
        Returns:
            Dictionary in clean JSON format ready for export
        """
        try:
            # Extract the actual field data
            extracted_fields = validated_data.get('extracted_data', {})
            
            # Create clean JSON structure
            json_data = {
                'export_id': f"EXPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'timestamp': datetime.now().isoformat(),
                'source_document': validated_data.get('source_document', validated_data.get('filename', 'unknown')),
                'validation_status': 'complete',
                'plan_data': extracted_fields,  # The actual mandatory fields (name, address, phone, etc.)
                'metadata': {
                    'all_fields_present': validated_data.get('all_fields_present', True),
                    'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'fields_extracted': list(extracted_fields.keys())
                }
            }
            
            logger.info(f"Converted data to JSON format - Export ID: {json_data['export_id']}")
            return json_data
            
        except Exception as e:
            logger.error(f"Error converting to JSON format: {str(e)}")
            raise
    
    def save_to_network_folder(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save JSON data to network shared folder
        
        Args:
            data: Data in JSON format
            
        Returns:
            Result dictionary with status
        """
        try:
            export_id = data.get('export_id', f"EXPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            source_doc = Path(data.get('source_document', 'unknown')).stem
            
            # Create filename: YYYYMMDD_HHMMSS_original_filename.json
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{source_doc}.json"
            filepath = self.export_path / filename
            
            logger.info(f"Saving data to network folder: {filepath}")
            
            # Write JSON file with nice formatting
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Verify file was created
            if filepath.exists():
                file_size = filepath.stat().st_size
                logger.info(f"✓ Successfully saved to network folder - Size: {file_size} bytes")
                
                return {
                    'success': True,
                    'status': 'exported',
                    'export_id': export_id,
                    'filepath': str(filepath),
                    'filename': filename,
                    'file_size': file_size,
                    'message': 'Data successfully exported to network folder',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.error("✗ File was not created")
                return {
                    'success': False,
                    'status': 'failed',
                    'export_id': export_id,
                    'error': 'File was not created after write attempt',
                    'timestamp': datetime.now().isoformat()
                }
                
        except PermissionError as e:
            logger.error(f"✗ Permission denied writing to network folder: {str(e)}")
            return {
                'success': False,
                'status': 'permission_error',
                'export_id': data.get('export_id'),
                'error': f'Permission denied: {str(e)}',
                'error_details': 'Check network folder permissions',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"✗ Error saving to network folder: {str(e)}")
            return {
                'success': False,
                'status': 'error',
                'export_id': data.get('export_id'),
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def validate_export_path(self) -> bool:
        """
        Validate that export path is accessible
        
        Returns:
            True if path is accessible and writable
        """
        try:
            # Try to create a test file
            test_file = self.export_path / '.test_write_access'
            test_file.write_text('test')
            test_file.unlink()  # Delete test file
            
            logger.info("✓ Export path is accessible and writable")
            return True
            
        except Exception as e:
            logger.warning(f"⚠ Export path validation failed: {str(e)}")
            return False
    
    def get_export_summary(self, export_path: str = None) -> Dict[str, Any]:
        """
        Get summary of exported files
        
        Args:
            export_path: Optional specific path to check (uses default if not provided)
            
        Returns:
            Summary dictionary
        """
        try:
            path_to_check = Path(export_path) if export_path else self.export_path
            
            json_files = list(path_to_check.glob('*.json'))
            
            total_size = sum(f.stat().st_size for f in json_files)
            
            return {
                'export_path': str(path_to_check),
                'total_files': len(json_files),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'accessible': path_to_check.exists()
            }
            
        except Exception as e:
            logger.error(f"Error getting export summary: {str(e)}")
            return {
                'export_path': str(self.export_path),
                'error': str(e)
            }
    
    def create_export_log(self, data: Dict[str, Any], result: Dict[str, Any], 
                         log_path: str = None):
        """
        Create a detailed log of the export operation (optional)
        
        Args:
            data: Original data exported
            result: Export result
            log_path: Path to save logs (optional)
        """
        if not log_path:
            return
        
        try:
            log_path = Path(log_path)
            log_path.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'export_id': data.get('export_id'),
                'exported_data': data,
                'export_result': result,
                'success': result.get('success', False)
            }
            
            filename = f"{data.get('export_id', 'unknown')}_log.json"
            filepath = log_path / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created export log: {filepath}")
            
        except Exception as e:
            logger.error(f"Error creating export log: {str(e)}")