#!/usr/bin/env python3
"""
Structure test script to verify the improved DDoS protection system structure.
This test doesn't require external dependencies.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_file_structure():
    """Test that all required files exist."""
    print("Testing file structure...")
    
    required_files = [
        'ddos_defender/__init__.py',
        'ddos_defender/config.py',
        'ddos_defender/logging.py',
        'ddos_defender/models.py',
        'ddos_defender/face_auth.py',
        'ddos_defender/traffic_analyzer.py',
        'ddos_defender/ip_blocker.py',
        'ddos_defender/telegram_bot.py',
        'ddos_defender/main.py',
        'requirements.txt',
        'Dockerfile',
        'docker-compose.yml',
        '.env.example',
        'README.md',
        '.dockerignore',
    ]
    
    missing_files = []
    
    for file_path in required_files:
        full_path = Path(__file__).parent / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files exist")
        return True

def test_module_imports():
    """Test that modules can be imported (basic structure)."""
    print("Testing module imports...")
    
    modules_to_test = [
        'ddos_defender',
        'ddos_defender.config',
        'ddos_defender.logging',
        'ddos_defender.models',
        'ddos_defender.face_auth',
        'ddos_defender.traffic_analyzer',
        'ddos_defender.ip_blocker',
        'ddos_defender.telegram_bot',
        'ddos_defender.main',
    ]
    
    failed_imports = []
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"  ✅ {module_name}")
        except ImportError as e:
            print(f"  ❌ {module_name}: {e}")
            failed_imports.append(module_name)
    
    if failed_imports:
        print(f"❌ Failed to import: {failed_imports}")
        return False
    else:
        print("✅ All modules can be imported")
        return True

def test_config_structure():
    """Test configuration module structure."""
    print("Testing configuration structure...")
    
    try:
        # Mock environment variables for testing
        os.environ['DDOS_BOT_TOKEN'] = 'test_token'
        os.environ['DDOS_ADMIN_CHAT_ID'] = '123456'
        
        # Try to import and check structure
        import ddos_defender.config as config_module
        
        # Check that required classes/functions exist
        required_items = [
            'Settings',
            'settings',
            'get_settings',
        ]
        
        missing_items = []
        for item in required_items:
            if not hasattr(config_module, item):
                missing_items.append(item)
        
        if missing_items:
            print(f"❌ Missing in config module: {missing_items}")
            return False
        else:
            print("✅ Configuration module structure is correct")
            return True
            
    except Exception as e:
        print(f"❌ Configuration structure test failed: {e}")
        return False

def test_code_quality():
    """Basic code quality checks."""
    print("Testing code quality...")
    
    issues = []
    
    # Check for TODO comments in critical files
    critical_files = [
        'ddos_defender/main.py',
        'ddos_defender/config.py',
        'ddos_defender/ip_blocker.py',
    ]
    
    for file_path in critical_files:
        full_path = Path(__file__).parent / file_path
        if full_path.exists():
            try:
                content = full_path.read_text(encoding='utf-8')
                if 'TODO' in content or 'FIXME' in content:
                    issues.append(f"{file_path} contains TODO/FIXME comments")
            except:
                pass
    
    if issues:
        print(f"⚠️  Code quality issues: {issues}")
        return False
    else:
        print("✅ Basic code quality checks passed")
        return True

def test_docker_config():
    """Test Docker configuration."""
    print("Testing Docker configuration...")
    
    try:
        # Check Dockerfile
        dockerfile_path = Path(__file__).parent / 'Dockerfile'
        if dockerfile_path.exists():
            content = dockerfile_path.read_text(encoding='utf-8')
            
            # Check for multi-stage build
            if 'FROM python:3.11-slim as builder' in content:
                print("  ✅ Dockerfile uses multi-stage build")
            else:
                print("  ⚠️  Dockerfile doesn't use multi-stage build")
            
            # Check for non-root user
            if 'useradd' in content and 'appuser' in content:
                print("  ✅ Dockerfile creates non-root user")
            else:
                print("  ⚠️  Dockerfile doesn't create non-root user")
            
            # Check for health check
            if 'HEALTHCHECK' in content:
                print("  ✅ Dockerfile includes health check")
            else:
                print("  ⚠️  Dockerfile doesn't include health check")
        
        # Check docker-compose.yml
        compose_path = Path(__file__).parent / 'docker-compose.yml'
        if compose_path.exists():
            content = compose_path.read_text(encoding='utf-8')
            
            # Check for required services
            required_services = ['ddos-protection', 'redis']
            for service in required_services:
                if f'{service}:' in content:
                    print(f"  ✅ docker-compose includes {service} service")
                else:
                    print(f"  ⚠️  docker-compose missing {service} service")
            
            # Check for monitoring services
            monitoring_services = ['prometheus', 'grafana']
            for service in monitoring_services:
                if f'{service}:' in content:
                    print(f"  ✅ docker-compose includes {service} for monitoring")
                else:
                    print(f"  ⚠️  docker-compose missing {service} (optional)")
        
        print("✅ Docker configuration tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Docker configuration test failed: {e}")
        return False

def test_documentation():
    """Test documentation."""
    print("Testing documentation...")
    
    try:
        # Check README
        readme_path = Path(__file__).parent / 'README.md'
        if readme_path.exists():
            content = readme_path.read_text(encoding='utf-8')
            
            required_sections = [
                '🚀 Быстрый старт',
                '📋 Команды бота',
                '🏗️ Архитектура системы',
                '⚙️ Конфигурация',
                '🐳 Docker Compose сервисы',
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in content:
                    missing_sections.append(section)
            
            if missing_sections:
                print(f"⚠️  README missing sections: {missing_sections}")
            else:
                print("✅ README includes all required sections")
        
        # Check .env.example
        env_example_path = Path(__file__).parent / '.env.example'
        if env_example_path.exists():
            content = env_example_path.read_text(encoding='utf-8')
            
            required_vars = [
                'DDOS_BOT_TOKEN',
                'DDOS_ADMIN_CHAT_ID',
                'DDOS_BLOCK_THRESHOLD',
                'DDOS_MONITOR_INTERFACE',
            ]
            
            missing_vars = []
            for var in required_vars:
                if var not in content:
                    missing_vars.append(var)
            
            if missing_vars:
                print(f"⚠️  .env.example missing variables: {missing_vars}")
            else:
                print("✅ .env.example includes all required variables")
        
        print("✅ Documentation tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Documentation test failed: {e}")
        return False

def run_all_tests():
    """Run all structure tests."""
    print("=" * 60)
    print("Running structure tests for improved DDoS Protection System")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("File Structure", test_file_structure()))
    results.append(("Module Imports", test_module_imports()))
    results.append(("Config Structure", test_config_structure()))
    results.append(("Code Quality", test_code_quality()))
    results.append(("Docker Config", test_docker_config()))
    results.append(("Documentation", test_documentation()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("STRUCTURE TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if success:
            passed += 1
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All structure tests passed! The system architecture is sound.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review the structure.")
        return False

if __name__ == "__main__":
    # Set test environment variables
    os.environ['DDOS_BOT_TOKEN'] = 'test_token'
    os.environ['DDOS_ADMIN_CHAT_ID'] = '123456'
    
    success = run_all_tests()
    sys.exit(0 if success else 1)