#!/usr/bin/env python3
"""
Basic test script to verify the improved DDoS protection system.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_config_module():
    """Test configuration module."""
    print("Testing configuration module...")
    try:
        from ddos_defender.config import get_settings
        
        # Create test environment variables
        os.environ['DDOS_BOT_TOKEN'] = 'test_token'
        os.environ['DDOS_ADMIN_CHAT_ID'] = '123456'
        
        settings = get_settings()
        
        # Test basic settings
        assert settings.bot_token == 'test_token'
        assert settings.admin_chat_id == '123456'
        assert settings.block_threshold == 1000
        assert settings.auto_unblock_minutes == 60
        assert settings.monitor_interface == 'eth0'
        assert settings.monitor_port == 80
        
        print("✅ Configuration module test passed")
        return True
        
    except Exception as e:
        print(f"❌ Configuration module test failed: {e}")
        return False

def test_logging_module():
    """Test logging module."""
    print("Testing logging module...")
    try:
        from ddos_defender.logging import get_logger
        
        logger = get_logger('test_logger')
        logger.info("Test log message")
        
        print("✅ Logging module test passed")
        return True
        
    except Exception as e:
        print(f"❌ Logging module test failed: {e}")
        return False

def test_models_module():
    """Test database models."""
    print("Testing database models...")
    try:
        from ddos_defender.models import Base, Admin, BlockedIP, Database
        
        # Test model creation
        db = Database()
        
        # Test table creation (in memory)
        import tempfile
        import sqlalchemy as sa
        
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        
        engine = sa.create_engine(f'sqlite:///{temp_db.name}')
        Base.metadata.create_all(engine)
        
        # Clean up
        os.unlink(temp_db.name)
        
        print("✅ Database models test passed")
        return True
        
    except Exception as e:
        print(f"❌ Database models test failed: {e}")
        return False

def test_face_auth_module():
    """Test face authentication module."""
    print("Testing face authentication module...")
    try:
        from ddos_defender.face_auth import FaceAuthenticator
        
        # Test initialization
        authenticator = FaceAuthenticator()
        
        # Test face quality verification (without actual image)
        quality_result = authenticator.verify_face_quality(__file__)  # Using this file as dummy
        
        # Should return error since it's not an image
        assert not quality_result['valid']
        assert 'error' in quality_result
        
        print("✅ Face authentication module test passed")
        return True
        
    except Exception as e:
        print(f"❌ Face authentication module test failed: {e}")
        return False

def test_ip_blocker_module():
    """Test IP blocker module."""
    print("Testing IP blocker module...")
    try:
        from ddos_defender.ip_blocker import IPBlocker
        
        # Test initialization
        ip_blocker = IPBlocker()
        
        # Test Redis connection (should fail in test environment)
        assert ip_blocker.redis is not None
        
        print("✅ IP blocker module test passed")
        return True
        
    except Exception as e:
        print(f"❌ IP blocker module test failed: {e}")
        return False

def test_traffic_analyzer_module():
    """Test traffic analyzer module."""
    print("Testing traffic analyzer module...")
    try:
        from ddos_defender.traffic_analyzer import SlidingWindowCounter
        
        # Test sliding window counter
        counter = SlidingWindowCounter(window_size=10)
        
        # Add events
        counter.add_event('192.168.1.1')
        counter.add_event('192.168.1.1')
        counter.add_event('192.168.1.2')
        
        # Test counts
        assert counter.get_count('192.168.1.1') == 2
        assert counter.get_count('192.168.1.2') == 1
        assert counter.get_count('192.168.1.3') == 0
        
        print("✅ Traffic analyzer module test passed")
        return True
        
    except Exception as e:
        print(f"❌ Traffic analyzer module test failed: {e}")
        return False

def test_telegram_bot_module():
    """Test Telegram bot module."""
    print("Testing Telegram bot module...")
    try:
        from ddos_defender.telegram_bot import TelegramBot
        
        # Test initialization
        bot = TelegramBot()
        
        # Test internal methods
        assert hasattr(bot, '_is_admin')
        assert hasattr(bot, '_is_authenticated')
        assert hasattr(bot, '_create_session')
        
        print("✅ Telegram bot module test passed")
        return True
        
    except Exception as e:
        print(f"❌ Telegram bot module test failed: {e}")
        return False

async def test_main_module():
    """Test main application module."""
    print("Testing main application module...")
    try:
        from ddos_defender.main import DDoSProtectionSystem
        
        # Test initialization
        system = DDoSProtectionSystem()
        
        assert hasattr(system, 'settings')
        assert hasattr(system, 'db')
        assert hasattr(system, 'traffic_analyzer')
        assert hasattr(system, 'telegram_bot')
        assert hasattr(system, 'ip_blocker')
        
        print("✅ Main application module test passed")
        return True
        
    except Exception as e:
        print(f"❌ Main application module test failed: {e}")
        return False

def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running tests for improved DDoS Protection System")
    print("=" * 60)
    
    results = []
    
    # Run synchronous tests
    results.append(("Configuration", test_config_module()))
    results.append(("Logging", test_logging_module()))
    results.append(("Database Models", test_models_module()))
    results.append(("Face Authentication", test_face_auth_module()))
    results.append(("IP Blocker", test_ip_blocker_module()))
    results.append(("Traffic Analyzer", test_traffic_analyzer_module()))
    results.append(("Telegram Bot", test_telegram_bot_module()))
    
    # Run async test
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        main_test_result = loop.run_until_complete(test_main_module())
        results.append(("Main Application", main_test_result))
        loop.close()
    except Exception as e:
        print(f"❌ Async test setup failed: {e}")
        results.append(("Main Application", False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for module_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{module_name:25} {status}")
        if success:
            passed += 1
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! The improved system is ready.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Some functionality may not work.")
        return False

if __name__ == "__main__":
    # Set test environment variables
    os.environ['DDOS_BOT_TOKEN'] = 'test_token'
    os.environ['DDOS_ADMIN_CHAT_ID'] = '123456'
    os.environ['DDOS_LOG_LEVEL'] = 'ERROR'  # Reduce log noise
    
    success = run_all_tests()
    sys.exit(0 if success else 1)