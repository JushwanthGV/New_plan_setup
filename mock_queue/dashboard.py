"""
Agentic AI - Live Dashboard (demo-optimized)
- Dynamically calculates column widths to keep borders aligned.
- Removes "..." ellipses and uses hard truncation/padding so the table looks neat.
- Shows business-level retry/registry summary at the bottom (reads data/retry_registry.json).
- Implements interactive controls: [C]lear Queue, [P]ause/Unpause, [Q]uit (via Ctrl+C).
"""
import os
import time
import json
import shutil
import sys # Added for input handling
from wcwidth import wcswidth # Used for correct width calculation of multi-byte characters

# --- Mock/Fallback Imports ---
# These assume necessary variables/classes are defined in external files, 
# but provide safe fallbacks for standalone execution/demonstration.
try:
    from queue_manager import QueueManager
    from config import *
except ImportError:
    # Fallback definitions for local execution environment
    DEFAULT_REFRESH_RATE = 2
    
    class QueueManager:
        def __init__(self, db_path):
            pass
        def get_all_items(self):
            return []
        def get_statistics(self):
            return {}
        def clear_all_items(self):
            pass
    QUEUE_DATABASE = "mock_db_path.json"


# Where the persistent retry registry lives (for business summary)
# NOTE: This path is unlikely to exist outside the original project structure, 
# so safe_load_registry will likely return an empty dict, which is handled gracefully.
RETRY_REGISTRY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "retry_registry.json")


def pad_display(text, width):
    """
    Truncates text based on display width (handling wide characters like emojis) 
    and pads the result with spaces to exactly match the target display width.
    """
    text = str(text)
    
    # 1. Truncate (if necessary)
    trimmed_text = ""
    current_width = 0
    for ch in text:
        ch_w = wcswidth(ch)
        if ch_w < 0:
            ch_w = 1 # Fallback for unknown characters (assume width 1)
        
        if current_width + ch_w > width:
            break
        
        trimmed_text += ch
        current_width += ch_w
        
    # 2. Pad (if necessary)
    padding_needed = width - current_width
    return trimmed_text + " " * max(0, padding_needed)


def safe_load_registry():
    """Safely loads the retry registry JSON file."""
    try:
        with open(RETRY_REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# Note: The original 'trunc_no_ellipsis' is removed as 'pad_display' now handles 
# both display-width-aware truncation and padding in one function.

class QueueDashboard:
    def __init__(self, queue_manager: QueueManager):
        self.queue = queue_manager
        self.refresh_rate = DEFAULT_REFRESH_RATE if 'DEFAULT_REFRESH_RATE' in globals() else 2
        self.paused = False

    def clear_screen(self):
        """Clears the console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def compute_layout(self, items):
        """Calculates dynamic column widths based on terminal size."""
        # Terminal width
        try:
            term_width = shutil.get_terminal_size().columns
        except Exception:
            term_width = 140

        # Minimum widths for columns (must be reasonable for small terminals)
        min_w = {
            "ID": 16,
            "Status": 10,
            "Plan": 10,
            "Sender": 18,
            "Try": 4,
            "Exception": 28,
            "Worker": 12
        }

        # Preferred (starting) widths
        pref = {
            "ID": 20,
            "Status": 12,
            "Plan": 12,
            "Sender": 25,
            "Try": 5,
            "Exception": 40,
            "Worker": 18
        }

        # Separators and paddings: Each column is bordered by "│ " or " │ "
        # 7 columns means 6 separators, plus 2 outer borders.
        # Total padding calculation is complex with emojis, so we estimate based on preferred setup.
        # Column format: <start_border><pad_display>│<space><pad_display>│<space>...<end_border>
        # Separator count: 6 * (2 spaces + 1 char) + 2 outer chars = 20 (approx)
        padding = 14 
        
        # compute base total
        base_total = sum(pref.values()) + padding

        # If terminal is wide enough, scale exception & worker to use extra space
        if term_width >= base_total:
            extra = term_width - base_total
            # distribute extra to Exception and Worker proportionally
            add_exc = int(extra * 0.65)
            add_work = extra - add_exc
            pref["Exception"] += add_exc
            pref["Worker"] += add_work
        else:
            # Need to shrink - reduce Exception and Sender first, respecting min widths
            deficit = base_total - term_width
            # shrink order: Exception, Sender, ID, Plan, Worker
            shrink_order = ["Exception", "Sender", "ID", "Plan", "Worker"]
            for key in shrink_order:
                if deficit <= 0:
                    break
                can_shrink = pref[key] - min_w[key]
                take = min(can_shrink, deficit)
                pref[key] -= take
                deficit -= take
            # Fallback: reduce everything proportionally but keep min
            if deficit > 0:
                for k in pref:
                    allow = pref[k] - min_w[k]
                    if allow > 0:
                        take = min(allow, deficit)
                        pref[k] -= take
                        deficit -= take
                        if deficit <= 0:
                            break

        # Final widths (ensuring at least min)
        for k in pref:
            pref[k] = max(pref[k], min_w[k])

        # Recalculate W based on final widths and padding, then fit to terminal
        W = sum(pref.values()) + padding
        W = min(W, term_width - 2) 
        
        return pref, W

    def get_status_display(self, status: str, retry_count: int = 0) -> str:
        """Converts internal status string to display-friendly string with emojis."""
        if status == 'Completed':
            return '✅ Completed'
        elif status == 'Locked':
            return '🔒 Processing'
        elif status == 'Exception':
            return '⚠️ Exception' if retry_count < 2 else '❌ Failed (2x)'
        elif status == 'Pending':
            return f'🔄 Retry #{retry_count}' if retry_count >= 1 else '⏳ Pending'
        elif status == 'Retry Queued':
            return '🔄 Retrying'
        elif status == 'Escalated':
            return '🚨 Escalated'
        elif status == 'User Notified':
            return '📩 Notified'
        else:
            return status

    def get_sender_email(self, item_data: dict) -> str:
        """Extracts sender email from item data."""
        try:
            return item_data.get('_requester_email') or item_data.get('sender_email') or 'N/A'
        except Exception:
            return 'N/A'
    
    def _get_mock_items(self):
        """Mock data for running the dashboard without a live QueueManager."""
        return [
            {'id': 'req-987654', 'status': 'Locked', 'retry_count': 0, 'plan_id': 'P-001', 'original_plan_id': 'P-001', 'data': {'_requester_email': 'alice@corp.com'}, 'vdi_assigned': 'worker-vdi-03'},
            {'id': 'req-123456', 'status': 'Completed', 'retry_count': 0, 'plan_id': 'P-002', 'original_plan_id': 'P-002', 'data': {'_requester_email': 'bob@corp.com'}, 'vdi_assigned': 'worker-vdi-01'},
            {'id': 'req-222444', 'status': 'Pending', 'retry_count': 0, 'plan_id': 'P-003', 'original_plan_id': 'P-003', 'data': {'_requester_email': 'charlie@corp.com'}, 'vdi_assigned': '-'},
            {'id': 'req-333111', 'status': 'Exception', 'retry_count': 1, 'plan_id': 'P-004-R1', 'original_plan_id': 'P-004', 'data': {'_requester_email': 'david@corp.com'}, 'exception_reason': 'API Timeout (Stage 2)', 'vdi_assigned': 'worker-vdi-02'},
            {'id': 'req-789012', 'status': 'User Notified', 'retry_count': 2, 'plan_id': 'P-005-R2', 'original_plan_id': 'P-005', 'data': {'_requester_email': 'eve@corp.com'}, 'exception_reason': 'Input missing, awaiting user fix', 'vdi_assigned': '-'},
            {'id': 'req-555666', 'status': 'Escalated', 'retry_count': 2, 'plan_id': 'P-006-E', 'original_plan_id': 'P-006', 'data': {'_requester_email': 'frank@corp.com'}, 'exception_reason': 'Unrecoverable state', 'vdi_assigned': '-'},
            {'id': 'req-777888', 'status': 'Retry Queued', 'retry_count': 1, 'plan_id': 'P-007', 'original_plan_id': 'P-007', 'data': {'_requester_email': 'grace@corp.com'}, 'vdi_assigned': '-'},
        ]

    def _get_mock_stats(self, items):
        """Computes mock statistics from mock items."""
        stats = {'total': len(items), 'pending': 0, 'locked': 0, 'completed': 0, 'exception': 0, 'user_notified': 0, 'retry_queued': 0, 'escalated': 0}
        for item in items:
            status = item.get('status', 'Unknown').lower().replace(' ', '_')
            if status in stats:
                stats[status] = stats.get(status, 0) + 1
        return stats

    def render_dashboard(self):
        """Renders the entire dashboard to the console."""
        self.clear_screen()
        # Handle mock data if QueueManager is not fully available
        try:
            items = self.queue.get_all_items()
            stats = self.queue.get_statistics()
        except AttributeError:
            items = self._get_mock_items()
            stats = self._get_mock_stats(items)
            
        registry = safe_load_registry()

        # compute layout widths
        pref, W = self.compute_layout(items)

        # helper for borders
        top_border = "╔" + "═" * W + "╗"
        mid_border = "╠" + "═" * W + "╣"
        bottom_border = "╚" + "═" * W + "╝"

        # header line
        print(top_border)
        center_title = "AGENTIC AI - LIVE DASHBOARD"
        title_space = W - len(center_title)
        left_pad = title_space // 2
        right_pad = title_space - left_pad
        print("║" + " " * left_pad + center_title + " " * right_pad + "║")
        print(mid_border)

        # stats line - use wcswidth for accurate padding around emojis
        stats_line_content = f" 📊 TOTAL: {stats.get('total',0):<3} | ⏳ Pending: {stats.get('pending',0):<3} | 🔒 Working: {stats.get('locked',0):<3} | ✅ Done: {stats.get('completed',0):<3} | ⚠️  Errors: {stats.get('exception',0):<3} | 📩 Notified: {stats.get('user_notified',0):<3}"
        
        display_width = wcswidth(stats_line_content)
        stats_padding = W - display_width
        print("║" + stats_line_content + " " * max(0, stats_padding) + "║")

        print(mid_border)

        # Header row using computed widths
        header = (
            f"║ {pad_display('ID', pref['ID'])}│ "
            f"{pad_display('Status', pref['Status'])}│ "
            f"{pad_display('Plan ID', pref['Plan'])}│ "
            f"{pad_display('Sender Email', pref['Sender'])}│ "
            f"{pad_display('Try', pref['Try'])}│ "
            f"{pad_display('Last Exception / Status', pref['Exception'])}│ "
            f"{pad_display('Worker', pref['Worker'])} ║"
        )
        print(header)
        print(mid_border)

        # If no items
        if not items:
            no_items_msg = "No items in queue"
            no_items_pad = W - len(no_items_msg)
            left_pad = no_items_pad // 2
            right_pad = no_items_pad - left_pad
            no_items = "║" + " " * left_pad + no_items_msg + " " * right_pad + "║"
            print(no_items)
        else:
            # Show last N items (keep last 15 as before)
            for item in items[-15:]:
                item_id = pad_display(item.get('id',''), pref['ID'])
                
                # Status
                status_raw = self.get_status_display(item.get('status',''), item.get('retry_count',0))
                status = pad_display(status_raw, pref['Status'])

                # Plan ID
                current_plan = item.get('plan_id','')
                original_plan = item.get('original_plan_id', current_plan)
                if current_plan != original_plan:
                    # Mark retried plans with '*'
                    plan_display = "*" + current_plan 
                else:
                    plan_display = current_plan
                plan_display = pad_display(plan_display, pref['Plan'])

                # Sender
                sender_raw = self.get_sender_email(item.get('data', {}))
                sender = pad_display(sender_raw, pref['Sender'])
                
                # Retry Count
                retry_raw = str(item.get('retry_count', 0))
                retry = pad_display(retry_raw, pref['Try'])

                # Exception Message
                exception_msg = item.get('exception_reason') or "OK"
                if item.get('status') == 'User Notified':
                    exception_msg = "Waiting for User Action"
                elif item.get('status') == 'Escalated':
                    # compute retries to display (retries = total attempts - 1)
                    orig_plan = item.get('original_plan_id', item.get('plan_id'))
                    rec = registry.get(orig_plan, {})
                    total_attempts = len(rec.get('attempts', [])) if isinstance(rec.get('attempts', []), list) else rec.get('retry_count', 0) + 1
                    retries = max(0, total_attempts - 1)
                    exception_msg = f"ESCALATED ({retries} retries)"
                elif item.get('status') == 'Retry Queued':
                    exception_msg = "Retry in Progress"
                exception = pad_display(exception_msg, pref['Exception'])

                # Worker / VDI
                vdi_value = item.get('vdi_assigned', '-')
                vdi = pad_display(vdi_value, pref['Worker'])

                row = (
                    f"║ {item_id}│ "
                    f"{status}│ "
                    f"{plan_display}│ "
                    f"{sender}│ "
                    f"{retry}│ "
                    f"{exception}│ "
                    f"{vdi} ║"
                )
                print(row)

        print(bottom_border)

        # Business summary (read registry)
        print("\n📈 BUSINESS TRACKING SUMMARY:")
        if registry:
            escalated_count = sum(1 for r in registry.values() if r.get('status') == 'ESCALATED')
            in_progress_count = sum(1 for r in registry.values() if r.get('status') == 'IN_PROGRESS')
            print(f"🚨 {escalated_count} Plan ID(s) have been ESCALATED (no more retries)")
            print(f"🔁 {in_progress_count} Plan ID(s) currently IN PROGRESS")
            print("\nRecent Escalations:")
            # list up to 5 most recent escalated records
            sorted_regs = sorted(
                [(k, v) for k, v in registry.items() if v.get('status') == 'ESCALATED'],
                key=lambda kv: kv[1].get('last_updated', ""),
                reverse=True
            )
            for plan_id, rec in sorted_regs[:5]:
                attempts = len(rec.get('attempts', [])) if isinstance(rec.get('attempts', []), list) else rec.get('retry_count', 0) + 1
                print(f"• Plan ID: {plan_id} | Attempts: {attempts} | Last: {rec.get('last_updated','N/A')}")
        else:
            print("No retry records found.")
        
        # Display control information
        print(f"\n🔄 Auto-refresh: {self.refresh_rate}s | Status: {'PAUSED' if self.paused else 'RUNNING'} | Controls: [C]lear Queue | [P]ause/Unpause | [Q]uit (via Ctrl+C)")

    def run(self):
        """Runs the dashboard loop, handling refresh and interactive controls via Ctrl+C."""
        
        try:
            while True:
                self.render_dashboard()
                
                if not self.paused:
                    # RUNNING state: Sleep for refresh rate. Ctrl+C breaks sleep.
                    try:
                        time.sleep(self.refresh_rate)
                    except KeyboardInterrupt:
                        # Ctrl+C is pressed, enter command handling mode
                        print("\n--- Command Mode ---")
                        command = input("Enter command [C/P/Q]: ").strip().lower()
                        
                        if command == 'q':
                            break # Quit the main loop
                        elif command == 'p':
                            self.paused = True
                            print("Dashboard PAUSED. Press ENTER to refresh now, or enter a command.")
                            time.sleep(0.5)
                            continue
                        elif command == 'c':
                            print("Clearing all items from the queue...")
                            try:
                                self.queue.clear_all_items()
                            except AttributeError:
                                print("[MOCK]: Queue cleared successfully.")
                            self.paused = False # Resume after clear for immediate feedback
                            print("Queue cleared. Resuming dashboard.")
                            time.sleep(1)
                            continue
                        else:
                            print("Resuming dashboard (Unknown command or no command entered).")
                            time.sleep(0.5)
                            continue
                        
                else:
                    # PAUSED state: Wait for command input (C, P, Q, or Enter to re-render)
                    print("\nPAUSED. Enter a command: [C]lear Queue, [P]ause (Unpause), [Q]uit, or just ENTER to re-render.")
                    
                    try:
                        command = input(">>> ").strip().lower()
                        
                        if command == 'c':
                            print("Clearing all items from the queue...")
                            try:
                                self.queue.clear_all_items()
                            except AttributeError:
                                print("[MOCK]: Queue cleared successfully.")
                            self.paused = False # Resume after command execution
                            print("Queue cleared. Resuming dashboard.")
                            time.sleep(1)
                        elif command == 'p':
                            self.paused = False
                            print("Dashboard unpaused. Resuming refresh.")
                            time.sleep(1)
                        elif command == 'q':
                            break # Quit the loop
                        elif command:
                            print(f"Unknown command: '{command}'. Try C, P, or Q.")
                            time.sleep(1)
                        # If user just presses Enter in paused mode, the loop continues, causing a re-render.
                        
                    except KeyboardInterrupt:
                        break # Handle interrupt during input
                    except EOFError:
                        break # Handle end of file
        
        except KeyboardInterrupt:
             # Final catch for KeyboardInterrupt if it happens outside the input block
             pass

        self.clear_screen()
        print("\n👋 Dashboard closed")


def main():
    # Use a mock manager if the real one is unavailable
    class MockQueueManager:
        def __init__(self, db_path):
            pass
        def get_all_items(self):
            # This is handled by QueueDashboard._get_mock_items()
            return [] 
        def get_statistics(self):
            # This is handled by QueueDashboard._get_mock_stats()
            return {}
        def clear_all_items(self):
            pass
            
    try:
        if 'QueueManager' in locals() and issubclass(QueueManager, object) and QueueManager.__name__ != 'QueueManager':
            # Assume the external QueueManager is available and initialized
            queue = QueueManager(QUEUE_DATABASE)
        else:
            # Fallback to MockQueueManager
            queue = MockQueueManager(None) 
    except Exception:
        queue = MockQueueManager(None)

    dashboard = QueueDashboard(queue)
    dashboard.run()

if __name__ == "__main__":
    main()