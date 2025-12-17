
"""
System Verification Script
Run this BEFORE starting the main system to verify all components
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

def verify_system():
    """Verify all system components are ready"""
    
    print("="*80)
    print("EMAIL-TO-BP AUTOMATION - SYSTEM VERIFICATION")
    print("="*80)
    
    issues = []
    warnings = []
    
    # 1. Check directory structure
    print("\n1. Checking directory structure...")
    required_dirs = [
        'data',
        'data/inbox_attachments',
        'data/validated_documents',
        'data/pending_requests',
        'data/network_export',
        'data/export_logs',
        'data/logs',
        'mock_queue',
        'agents',
        'utils'
    ]
    
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"   ✅ {dir_path}")
        else:
            print(f"   ⚠️  {dir_path} - CREATING...")
            path.mkdir(parents=True, exist_ok=True)
            warnings.append(f"Created missing directory: {dir_path}")
    
    # 2. Check queue database
    print("\n2. Checking queue database...")
    queue_path = Path("data/queue.json")
    if queue_path.exists():
        print(f"   ✅ Queue database exists: {queue_path}")
        # Validate it's proper JSON
        try:
            with open(queue_path, 'r') as f:
                data = json.load(f)
                print(f"   ✅ Queue contains {len(data)} items")
        except json.JSONDecodeError:
            print(f"   ❌ Queue database corrupted!")
            issues.append("Queue database is corrupted - will be recreated")
            with open(queue_path, 'w') as f:
                json.dump([], f)
    else:
        print(f"   ⚠️  Queue database missing - CREATING...")
        with open(queue_path, 'w') as f:
            json.dump([], f)
        warnings.append(f"Created queue database: {queue_path}")
    
    # 3. Check environment variables
    print("\n3. Checking environment variables...")
    load_dotenv()
    
    required_env = {
        'EMAIL_ADDRESS': 'Email address for monitoring',
        'APP_PASSWORD': 'Email app password',
        'MONITOR_SENDER': 'Sender email to monitor',
        'MONITOR_SUBJECT': 'Email subject to monitor',
        'GROQ_API_KEY': 'Groq API key for LLM'
    }
    
    for var, description in required_env.items():
        value = os.getenv(var)
        if value:
            masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '*' * len(value)
            print(f"   ✅ {var}: {masked}")
        else:
            print(f"   ❌ {var}: NOT SET")
            issues.append(f"Missing environment variable: {var} ({description})")
    
    # 4. Check Python dependencies
    print("\n4. Checking critical dependencies...")
    critical_deps = {
        'langchain': 'LangChain framework',
        'langchain_groq': 'Groq integration',
        'langgraph': 'Workflow orchestration',
        'pytesseract': 'OCR support',
        'transformers': 'TrOCR models',
        'torch': 'PyTorch (for TrOCR)',
        'easyocr': 'Additional OCR',
        'PIL': 'Image processing'
    }
    
    for module, description in critical_deps.items():
        try:
            if module == 'PIL':
                __import__('PIL')
            else:
                __import__(module)
            print(f"   ✅ {module}")
        except ImportError:
            print(f"   ❌ {module} - NOT INSTALLED")
            issues.append(f"Missing dependency: {module} ({description})")
    
    # 5. Check config.py issue
    print("\n5. Checking mock_queue configuration...")
    config_file = Path("mock_queue/config.py")
    if config_file.exists():
        with open(config_file, 'r') as f:
            config_content = f.read()
            
        # Check for duplicate QUEUE_DATABASE definition
        if config_content.count('QUEUE_DATABASE') > 1:
            print("   ⚠️  WARNING: Multiple QUEUE_DATABASE definitions found!")
            warnings.append("config.py has duplicate QUEUE_DATABASE - using BASE_DIR version")
        else:
            print("   ✅ Config file looks good")
    else:
        print("   ❌ config.py not found!")
        issues.append("Missing mock_queue/config.py")
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    if not issues:
        print("✅ All critical checks passed!")
    else:
        print(f"❌ {len(issues)} critical issue(s) found:")
        for issue in issues:
            print(f"   - {issue}")
    
    if warnings:
        print(f"\n⚠️  {len(warnings)} warning(s):")
        for warning in warnings:
            print(f"   - {warning}")
    
    print("\n" + "="*80)
    
    if issues:
        print("\n❌ SYSTEM NOT READY - Fix issues above before running")
        return False
    else:
        print("\n✅ SYSTEM READY - You can now start the main system")
        return True

if __name__ == "__main__":
    success = verify_system()
    sys.exit(0 if success else 1)

