"""
Quick Start Script - Launches all components
"""

import subprocess
import sys
import time
from pathlib import Path

def start_all():
    """Start all system components in separate processes"""
    
    print("="*80)
    print("STARTING EMAIL-TO-BP AUTOMATION SYSTEM")
    print("="*80)
    
    # First verify system
    print("\nStep 1: Verifying system...")
    result = subprocess.run([sys.executable, "verify_system.py"])
    
    if result.returncode != 0:
        print("\n❌ System verification failed. Please fix issues first.")
        return
    
    print("\n✅ System verified!")
    time.sleep(2)
    
    print("\n" + "="*80)
    print("Starting components...")
    print("="*80)
    
    # Start components
    processes = []
    
    try:
        # 1. Start BP Worker
        print("\n1. Starting Blue Prism Worker...")
        worker = subprocess.Popen([sys.executable, "-m", "mock_queue.bp_worker"])
        processes.append(("BP Worker", worker))
        time.sleep(2)
        
        # 2. Start Main System (Agents 1-5)
        print("2. Starting Main System (Agents 1-5)...")
        main = subprocess.Popen([sys.executable, "main.py"])
        processes.append(("Main System", main))
        time.sleep(2)
        
        # 3. Start Dashboard
        print("3. Starting Dashboard...")
        dashboard = subprocess.Popen([sys.executable, "-m", "mock_queue.dashboard"])
        processes.append(("Dashboard", dashboard))
        
        print("\n" + "="*80)
        print("✅ ALL COMPONENTS STARTED")
        print("="*80)
        print("\nPress Ctrl+C to stop all components...\n")
        
        # Wait for all processes
        for name, proc in processes:
            proc.wait()
            
    except KeyboardInterrupt:
        print("\n\nStopping all components...")
        for name, proc in processes:
            proc.terminate()
            print(f"   ✅ Stopped {name}")
        
        print("\n✅ All components stopped")

if __name__ == "__main__":
    start_all()