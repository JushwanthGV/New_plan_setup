"""
Mock Blue Prism Queue Manager
Manages queue.json as the database for all queue items
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import random
import string

logger = logging.getLogger(__name__)

class QueueManager:
    """Manages the mock Blue Prism work queue"""
    
    def __init__(self, queue_file: str = "./queue.json"):
        """
        Initialize Queue Manager
        
        Args:
            queue_file: Path to queue database JSON file
        """
        self.queue_file = Path(queue_file)
        self._ensure_queue_exists()
        logger.info(f"Queue Manager initialized - Database: {queue_file}")
    
    def _ensure_queue_exists(self):
        """Create queue file if it doesn't exist"""
        if not self.queue_file.exists():
            self._write_queue([])
            logger.info(f"Created new queue database: {self.queue_file}")
    
    def _read_queue(self) -> List[Dict[str, Any]]:
        """Read all items from queue"""
        try:
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Queue file corrupted, recreating...")
            self._write_queue([])
            return []
        except Exception as e:
            logger.error(f"Error reading queue: {str(e)}")
            return []
    
    def _write_queue(self, items: List[Dict[str, Any]]):
        """Write items to queue"""
        try:
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error writing queue: {str(e)}")
            raise
    
    def add_item(self, data: Dict[str, Any], plan_id: str = None, 
                 original_plan_id: str = None, retry_count: int = 0,
                 retry_history: List[Dict] = None) -> str:
        """
        Add new item to queue
        
        Args:
            data: Plan data (name, address, phone_number, etc.)
            plan_id: Plan ID (auto-generated if not provided)
            original_plan_id: Original plan ID before retries
            retry_count: Number of retry attempts so far
            retry_history: List of previous retry attempts
            
        Returns:
            Queue item ID
        """
        items = self._read_queue()
        
        # Generate queue item ID
        item_id = f"QI_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(items)+1:03d}"
        
        # Generate plan ID if not provided
        if not plan_id:
            plan_id = self._generate_plan_id()
        
        # Create queue item
        item = {
            'id': item_id,
            'plan_id': plan_id,
            'original_plan_id': original_plan_id or plan_id,
            'status': 'Pending',
            'data': data,
            'vdi_assigned': 'VDI_Server_01',
            'retry_count': retry_count,
            'retry_history': retry_history or [],
            'exception_reason': None,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'locked_at': None,
            'completed_at': None
        }
        
        items.append(item)
        self._write_queue(items)
        
        logger.info(f"✓ Added item to queue: {item_id} (Plan ID: {plan_id}, Retry: {retry_count})")
        return item_id
    
    def _generate_plan_id(self) -> str:
        """Generate random 7-character alphanumeric Plan ID"""
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=7))
    
    def get_next_item(self) -> Optional[Dict[str, Any]]:
        """
        Get next pending item and lock it
        
        Returns:
            Queue item or None if no pending items
        """
        items = self._read_queue()
        
        # Find oldest pending item
        for item in items:
            if item['status'] == 'Pending':
                # Lock the item
                item['status'] = 'Locked'
                item['locked_at'] = datetime.now().isoformat()
                item['updated_at'] = datetime.now().isoformat()
                
                self._write_queue(items)
                logger.info(f"✓ Locked item: {item['id']} (Plan ID: {item['plan_id']})")
                return item
        
        return None
    
    def mark_completed(self, item_id: str) -> bool:
        """
        Mark item as completed
        
        Args:
            item_id: Queue item ID
            
        Returns:
            True if successful
        """
        items = self._read_queue()
        
        for item in items:
            if item['id'] == item_id:
                item['status'] = 'Completed'
                item['completed_at'] = datetime.now().isoformat()
                item['updated_at'] = datetime.now().isoformat()
                
                self._write_queue(items)
                logger.info(f"✓ Marked as completed: {item_id} (Plan ID: {item['plan_id']})")
                return True
        
        logger.warning(f"Item not found: {item_id}")
        return False
    
    def mark_exception(self, item_id: str, reason: str) -> bool:
        """
        Mark item as exception
        
        Args:
            item_id: Queue item ID
            reason: Exception reason
            
        Returns:
            True if successful
        """
        items = self._read_queue()
        
        for item in items:
            if item['id'] == item_id:
                item['status'] = 'Exception'
                item['exception_reason'] = reason
                item['updated_at'] = datetime.now().isoformat()
                
                self._write_queue(items)
                logger.info(f"✗ Marked as exception: {item_id} - {reason}")
                return True
        
        logger.warning(f"Item not found: {item_id}")
        return False
    
    def get_all_items(self) -> List[Dict[str, Any]]:
        """Get all queue items"""
        return self._read_queue()
    
    def get_items_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get items with specific status"""
        items = self._read_queue()
        return [item for item in items if item['status'] == status]
    
    def get_item_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get specific item by ID"""
        items = self._read_queue()
        for item in items:
            if item['id'] == item_id:
                return item
        return None
    
    def update_item(self, item_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update item fields
        
        Args:
            item_id: Queue item ID
            updates: Dictionary of fields to update
            
        Returns:
            True if successful
        """
        items = self._read_queue()
        
        for item in items:
            if item['id'] == item_id:
                item.update(updates)
                item['updated_at'] = datetime.now().isoformat()
                
                self._write_queue(items)
                logger.info(f"✓ Updated item: {item_id}")
                return True
        
        logger.warning(f"Item not found: {item_id}")
        return False
    
    def clear_queue(self):
        """Clear all items from queue (for testing)"""
        self._write_queue([])
        logger.info("Queue cleared")
    
    def get_statistics(self) -> Dict[str, int]:
        """Get queue statistics"""
        items = self._read_queue()
        
        stats = {
            'total': len(items),
            'pending': 0,
            'locked': 0,
            'completed': 0,
            'exception': 0,
            'retry_1': 0,
            'retry_2_failed': 0
        }
        
        for item in items:
            status = item['status']
            retry_count = item.get('retry_count', 0)
            
            if status == 'Pending':
                stats['pending'] += 1
                if retry_count == 1:
                    stats['retry_1'] += 1
            elif status == 'Locked':
                stats['locked'] += 1
            elif status == 'Completed':
                stats['completed'] += 1
            elif status == 'Exception':
                stats['exception'] += 1
                if retry_count >= 2:
                    stats['retry_2_failed'] += 1
        
        return stats