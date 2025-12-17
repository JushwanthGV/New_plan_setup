"""
Agentic AI – Live Queue Dashboard (Stable + VDI-safe)
"""

import time
import logging
import shutil
from wcwidth import wcwidth, wcswidth
from queue_manager import QueueManager
from config import *

logging.disable(logging.CRITICAL)

# ===================== WIDTH HELPERS =====================

def visual_len(text: str) -> int:
    return wcswidth(str(text))


def pad_to_width(text: str, width: int) -> str:
    diff = width - visual_len(text)
    return text + " " * diff if diff > 0 else text


def trunc(text: str, width: int) -> str:
    text = str(text)
    if visual_len(text) <= width:
        return pad_to_width(text, width)

    out, cur = "", 0
    for ch in text:
        w = max(wcwidth(ch), 0)
        if cur + w > width - 1:
            break
        out += ch
        cur += w
    return pad_to_width(out + "…", width)


def trunc_keep_right(text: str, width: int) -> str:
    text = str(text)
    if visual_len(text) <= width:
        return pad_to_width(text, width)

    out, cur = "", 0
    for ch in reversed(text):
        w = max(wcwidth(ch), 0)
        if cur + w > width - 1:
            break
        out = ch + out
        cur += w
    return pad_to_width("…" + out, width)

# ===================== DASHBOARD =====================

class QueueDashboard:

    def __init__(self, queue: QueueManager):
        self.queue = queue
        self.refresh_rate = DEFAULT_REFRESH_RATE
        self.W = max(100, shutil.get_terminal_size((120, 20)).columns - 2)

        self.cols = {
            "id": 18,
            "status": 18,
            "plan": 10,
            "sender": 22,
            "try": 4,
            "exception": 32,
            "worker": 12,   # slightly wider for VDI numbers
        }

    def clear(self):
        print("\033[H\033[J", end="")

    def status_display(self, status, retry):
        if status == "Completed":
            return "✅ Completed"
        if status == "Locked":
            return "🔒 Processing"
        if status == "Exception":
            return "❌ Failed" if retry >= 2 else "⚠️ Exception"
        if status == "Pending":
            return f"🔄 Retry {retry}" if retry else "⏳ Pending"
        if status == "User Notified":
            return "📩 Notified"
        return status

    # ===================== RENDER =====================

    def render_header(self, stats):
        W = self.W
        print("╔" + "═" * W + "╗")
        print("║" + pad_to_width("AGENTIC AI  –  LIVE DASHBOARD".center(W), W) + "║")
        print("╠" + "═" * W + "╣")

        line1 = (
            f"📊 TOTAL: {stats['total']} | "
            f"⏳ Pending: {stats['pending']} | "
            f"🔒 Working: {stats['locked']} | "
            f"✅ Done: {stats['completed']} | "
            f"⚠️ Errors: {stats['exception']} | "
            f"📩 Notified: {stats.get('user_notified', 0)}"
        )
        print("║" + pad_to_width(line1, W) + "║")

        line2 = (
            f"🔄 RETRIES: Attempt #1: {stats['retry_1']} | "
            f"❌ Failed Final: {stats['retry_2_failed']}"
        )
        print("║" + pad_to_width(line2, W) + "║")

        print("╠" + "═" * W + "╣")

        header = (
            f" {'ID'.ljust(self.cols['id'])} │ "
            f"{'Status'.ljust(self.cols['status'])} │ "
            f"{'Plan ID'.ljust(self.cols['plan'])} │ "
            f"{'Sender Email'.ljust(self.cols['sender'])} │ "
            f"{'Try'.ljust(self.cols['try'])} │ "
            f"{'Last Exception / Status'.ljust(self.cols['exception'])} │ "
            f"{'Worker'.ljust(self.cols['worker'])}"
        )
        print("║" + pad_to_width(header, W) + "║")
        print("╠" + "═" * W + "╣")

    def render_rows(self, items):
        if not items:
            print("║" + pad_to_width("No items in queue".center(self.W), self.W) + "║")
            return

        for item in items[-15:]:
            row = (
                f" {trunc(item['id'], self.cols['id'])} │ "
                f"{trunc(self.status_display(item['status'], item.get('retry_count', 0)), self.cols['status'])} │ "
                f"{trunc(item['plan_id'], self.cols['plan'])} │ "
                f"{trunc(item.get('data', {}).get('_requester_email', 'N/A'), self.cols['sender'])} │ "
                f"{trunc(item.get('retry_count', 0), self.cols['try'])} │ "
                f"{trunc(item.get('exception_reason') or 'OK', self.cols['exception'])} │ "
                f"{trunc_keep_right(item.get('vdi_assigned', '-'), self.cols['worker'])}"
            )
            print("║" + pad_to_width(row, self.W) + "║")

    def render_footer(self):
        print("╚" + "═" * self.W + "╝")
        print(f"\n🔄 Auto-refresh: {self.refresh_rate}s | Controls: [P]ause  [Q]uit")

    def run(self):
        try:
            while True:
                self.clear()
                items = self.queue.get_all_items()
                stats = self.queue.get_statistics()
                self.render_header(stats)
                self.render_rows(items)
                self.render_footer()
                time.sleep(self.refresh_rate)
        except KeyboardInterrupt:
            self.clear()
            print("👋 Dashboard closed")

# ===================== MAIN =====================

def main():
    dashboard = QueueDashboard(QueueManager(QUEUE_DATABASE))
    dashboard.run()

if __name__ == "__main__":
    main()
