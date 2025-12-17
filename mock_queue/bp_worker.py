"""
Mock Blue Prism Worker - MODIFIED FOR TESTING PLAN ID EXCEPTION
Simulates a Blue Prism robot processing queue items
"""

import time
import random
import logging
from queue_manager import QueueManager
from config import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [BP WORKER] - %(message)s'
)
logger = logging.getLogger(__name__)

class BluePrismWorker:
    """Simulates Blue Prism robot processing"""
    
    def __init__(self, queue_manager: QueueManager):
        """
        Initialize BP Worker
        
        Args:
            queue_manager: Instance of QueueManager
        """
        self.queue = queue_manager
        self.vdi_name = VDI_NAME
        
        # ═══════════════════════════════════════════════════════════
        # TESTING MODE: Track processed names to force duplicate Plan IDs
        # ═══════════════════════════════════════════════════════════
        self.processed_names = []  # Store names we've seen
        
        logger.info(f"✅ Blue Prism Worker initialized on {self.vdi_name}")
        logger.info("⚠️  TEST MODE: Will trigger 'Plan ID Exists' for duplicate names")
    
    def process_item(self, item: dict) -> tuple[bool, str]:
        """
        Process a single queue item
        
        Args:
            item: Queue item dictionary
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        item_id = item['id']
        plan_id = item['plan_id']
        data = item['data']
        customer_name = data.get('name', 'Unknown')
        
        logger.info(f"{'='*60}")
        logger.info(f"🤖 Processing Item: {item_id}")
        logger.info(f"📋 Plan ID: {plan_id}")
        logger.info(f"👤 Customer Name: {customer_name}")
        logger.info(f"🖥️  VDI: {self.vdi_name}")
        logger.info(f"📊 Data: {data}")
        logger.info(f"{'='*60}")
        
        # Simulate BP robot actions
        logger.info("▶ Step 1: Logging into application...")
        time.sleep(1)
        
        logger.info("▶ Step 2: Navigating to New Plan form...")
        time.sleep(0.5)
        
        logger.info(f"▶ Step 3: Entering Plan ID: {plan_id}")
        time.sleep(0.5)
        
        # ═══════════════════════════════════════════════════════════
        # TEST LOGIC: Force "Plan ID Exists" if we've seen this name before
        # ═══════════════════════════════════════════════════════════
        if customer_name in self.processed_names:
            logger.error(f"❌ EXCEPTION: {EXCEPTION_PLAN_EXISTS}")
            logger.error(f"   Plan ID '{plan_id}' conflicts with existing record")
            logger.error(f"   (Customer '{customer_name}' already processed)")
            return False, EXCEPTION_PLAN_EXISTS
        
        # Mark this name as processed
        self.processed_names.append(customer_name)
        logger.info(f"   📝 Stored customer name: {customer_name}")
        # ═══════════════════════════════════════════════════════════
        
        logger.info("▶ Step 4: Filling form fields...")
        logger.info(f"   - Name: {data.get('name', 'N/A')}")
        logger.info(f"   - Address: {data.get('address', 'N/A')}")
        logger.info(f"   - Phone: {data.get('phone_number', 'N/A')}")
        time.sleep(1)
        
        logger.info("▶ Step 5: Submitting form...")
        time.sleep(0.5)
        
        # Check if this is a demo exception case
        source_doc = item.get('data', {}).get('_source_document', '')
        
        if 'exception_data_error' in source_doc.lower():
            # Simulate data validation error
            logger.error(f"❌ EXCEPTION: {EXCEPTION_DATA_ERROR}")
            logger.error(f"   Phone number format invalid")
            return False, EXCEPTION_DATA_ERROR
        
        else:
            # Success case
            logger.info(f"✅ SUCCESS - Plan created with ID: {plan_id}")
            logger.info(f"✅ All validations passed")
            logger.info(f"✅ Customer '{customer_name}' added to processed list")
            return True, "Plan created successfully"
    
    def run_once(self) -> bool:
        """
        Process one item from queue
        
        Returns:
            True if an item was processed, False if queue is empty
        """
        logger.info("\n🔍 Polling queue for next item...")
        
        item = self.queue.get_next_item()
        
        if not item:
            logger.info("⊘ Queue is empty - no items to process")
            return False
        
        # Process the item
        success, message = self.process_item(item)
        
        if success:
            self.queue.mark_completed(item['id'])
            logger.info(f"✅ Item {item['id']} marked as COMPLETED\n")
        else:
            self.queue.mark_exception(item['id'], message)
            logger.error(f"❌ Item {item['id']} marked as EXCEPTION: {message}\n")
        
        return True
    
    def run_continuous(self, poll_interval: int = 5):
        """
        Run worker in continuous mode
        
        Args:
            poll_interval: Seconds to wait between polls
        """
        logger.info(f"{'='*60}")
        logger.info(f"🚀 BLUE PRISM WORKER STARTED")
        logger.info(f"🖥️  VDI: {self.vdi_name}")
        logger.info(f"⏱️  Poll Interval: {poll_interval} seconds")
        logger.info(f"⚠️  TEST MODE ACTIVE")
        logger.info(f"{'='*60}\n")
        logger.info("Press Ctrl+C to stop\n")
        
        try:
            while True:
                processed = self.run_once()
                
                if not processed:
                    logger.info(f"💤 Waiting {poll_interval} seconds before next poll...\n")
                    time.sleep(poll_interval)
                else:
                    # Small delay between items
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("\nℹ️  Worker stopped by user")
        except Exception as e:
            logger.error(f"\n❌ Worker error: {str(e)}")
            raise

def main():
    """Main entry point for BP Worker"""
    queue = QueueManager(QUEUE_DATABASE)
    worker = BluePrismWorker(queue)
    worker.run_continuous(poll_interval=5)

if __name__ == "__main__":
    main()