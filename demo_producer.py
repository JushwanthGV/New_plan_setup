"""
Demo Queue Item Producer
Manually inject test items into the BP queue for demonstration
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add mock_queue to path
sys.path.append(str(Path(__file__).parent / 'mock_queue'))

from mock_queue.queue_manager import QueueManager
from mock_queue.config import QUEUE_DATABASE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [PRODUCER] - %(message)s'
)
logger = logging.getLogger(__name__)

class DemoProducer:
    """Produces demo queue items for testing"""
    
    def __init__(self):
        """Initialize Demo Producer"""
        self.queue = QueueManager(QUEUE_DATABASE)
        logger.info("Demo Producer initialized")
    
    def add_success_case(self):
        """Add item that will succeed"""
        data = {
            'name': 'John Smith',
            'address': '123 Main Street, New York, NY 10001',
            'phone_number': '+1-555-0100',
            '_source_document': 'demo_success_case.pdf',
            '_requester_email': 'prajush01@gmail.com'
        }
        
        item_id = self.queue.add_item(data)
        logger.info(f"✓ Added SUCCESS case: {item_id}")
        return item_id
    
    def add_plan_exists_exception(self):
        """Add item that will trigger 'Plan ID exists' exception"""
        data = {
            'name': 'Jane Doe',
            'address': '456 Oak Avenue, Los Angeles, CA 90001',
            'phone_number': '+1-555-0200',
            '_source_document': 'demo_exception_plan_exists.pdf',
            '_requester_email': 'prajush01@gmail.com'
        }
        
        item_id = self.queue.add_item(data)
        logger.info(f"✓ Added PLAN EXISTS EXCEPTION case: {item_id}")
        return item_id
    
    def add_data_error_exception(self):
        """Add item that will trigger data validation error"""
        data = {
            'name': 'Bob Johnson',
            'address': '789 Pine Road, Chicago, IL 60601',
            'phone_number': 'INVALID_PHONE',
            '_source_document': 'demo_exception_data_error.pdf',
            '_requester_email': 'prajush01@gmail.com'
        }
        
        item_id = self.queue.add_item(data)
        logger.info(f"✓ Added DATA ERROR EXCEPTION case: {item_id}")
        return item_id
    
    def add_batch_items(self, count: int = 5):
        """Add multiple success items"""
        logger.info(f"Adding {count} batch items...")
        
        names = ['Alice Brown', 'Charlie Davis', 'Diana Wilson', 'Ethan Moore', 'Fiona Taylor']
        
        for i in range(min(count, len(names))):
            data = {
                'name': names[i],
                'address': f'{100+i*10} Test Street, Boston, MA 02101',
                'phone_number': f'+1-555-0{300+i}',
                '_source_document': f'demo_batch_{i+1}.pdf',
                '_requester_email': 'prajush01@gmail.com'
            }
            
            item_id = self.queue.add_item(data)
            logger.info(f"✓ Added batch item {i+1}/{count}: {item_id}")
    
    def show_menu(self):
        """Show interactive menu"""
        print("\n" + "="*60)
        print("DEMO QUEUE ITEM PRODUCER")
        print("="*60)
        print("\n1. Add Success Case (will complete successfully)")
        print("2. Add Plan ID Exists Exception (will retry with new ID)")
        print("3. Add Data Error Exception (will fail immediately)")
        print("4. Add 5 Batch Success Items")
        print("5. Show Queue Statistics")
        print("6. Clear Entire Queue")
        print("Q. Quit")
        print("\n" + "="*60)
    
    def show_statistics(self):
        """Display queue statistics"""
        stats = self.queue.get_statistics()
        
        print("\n" + "="*60)
        print("QUEUE STATISTICS")
        print("="*60)
        print(f"Total Items: {stats['total']}")
        print(f"Pending: {stats['pending']}")
        print(f"Locked (Processing): {stats['locked']}")
        print(f"Completed: {stats['completed']}")
        print(f"Exceptions: {stats['exception']}")
        print(f"Retry Attempt #1: {stats['retry_1']}")
        print(f"Failed After 2 Attempts: {stats['retry_2_failed']}")
        print("="*60 + "\n")
    
    def run_interactive(self):
        """Run interactive menu"""
        logger.info("Starting interactive mode...\n")
        
        while True:
            self.show_menu()
            
            choice = input("\nEnter your choice: ").strip().upper()
            
            if choice == '1':
                self.add_success_case()
            elif choice == '2':
                self.add_plan_exists_exception()
            elif choice == '3':
                self.add_data_error_exception()
            elif choice == '4':
                self.add_batch_items(5)
            elif choice == '5':
                self.show_statistics()
            elif choice == '6':
                confirm = input("\n⚠️  Clear entire queue? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    self.queue.clear_queue()
                    logger.info("✓ Queue cleared")
                else:
                    logger.info("Cancelled")
            elif choice == 'Q':
                logger.info("Exiting...")
                break
            else:
                print("\n❌ Invalid choice. Please try again.")
            
            input("\nPress Enter to continue...")

def main():
    """Main entry point"""
    producer = DemoProducer()
    producer.run_interactive()

if __name__ == "__main__":
    main()