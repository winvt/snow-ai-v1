#!/usr/bin/env python3
"""
Deployment Verification Script for Snow AI Dashboard
Checks all critical functionality before deployment
"""

import os
import sys
import subprocess
import importlib.util

def check_python_version():
    """Check Python version compatibility"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    else:
        print(f"  ❌ Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.8+")
        return False

def check_dependencies():
    """Check all required dependencies"""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'streamlit',
        'requests', 
        'pandas',
        'plotly',
        'python-dotenv',
        'pytz'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'python-dotenv':
                import dotenv
                version = getattr(dotenv, '__version__', 'Unknown')
                print(f"  ✅ {package} - {version}")
            else:
                module = importlib.import_module(package)
                version = getattr(module, '__version__', 'Unknown')
                print(f"  ✅ {package} - {version}")
        except ImportError:
            print(f"  ❌ {package} - Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n  📋 Missing packages: {', '.join(missing_packages)}")
        print("  💡 Run: pip install -r requirements.txt")
        return False
    
    return True

def check_files():
    """Check all required files exist"""
    print("\n📁 Checking required files...")
    
    required_files = [
        'app.py',
        'database.py', 
        'requirements.txt',
        'render.yaml',
        'start.sh'
    ]
    
    missing_files = []
    
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - Missing")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n  📋 Missing files: {', '.join(missing_files)}")
        return False
    
    return True

def check_database_functionality():
    """Test database functionality"""
    print("\n🗄️ Testing database functionality...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, os.getcwd())
        
        from database import LoyverseDB
        
        # Test database initialization
        db = LoyverseDB("test_deployment.db")
        print(f"  ✅ Database initialized at: {db.db_path}")
        
        # Test basic operations
        stats = db.get_database_stats()
        print(f"  ✅ Database stats retrieved: {len(stats)} fields")
        
        # Test connection
        conn = db.get_connection()
        conn.close()
        print("  ✅ Database connection successful")
        
        # Clean up
        if os.path.exists("test_deployment.db"):
            os.remove("test_deployment.db")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        return False

def check_translations():
    """Test translation system"""
    print("\n🌐 Testing translation system...")
    
    try:
        # Mock the translation system
        TRANSLATIONS = {
            "English": {
                "small": "Small",
                "medium": "Medium", 
                "large": "Large",
                "font_size": "Font Size"
            },
            "Thai": {
                "small": "เล็ก",
                "medium": "กลาง",
                "large": "ใหญ่",
                "font_size": "ขนาดตัวอักษร"
            }
        }
        
        def get_text(key, lang="English"):
            return TRANSLATIONS[lang].get(key, key)
        
        # Test both languages
        for lang in ["English", "Thai"]:
            options = [get_text("small", lang), get_text("medium", lang), get_text("large", lang)]
            print(f"  ✅ {lang} font options: {options}")
            
            # Test index finding
            medium_index = options.index(get_text("medium", lang))
            print(f"  ✅ {lang} medium index: {medium_index}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Translation test failed: {e}")
        return False

def check_environment_variables():
    """Check environment variable configuration"""
    print("\n🔧 Checking environment variables...")
    
    # Check if we're in a deployment environment
    if os.getenv('DATABASE_PATH'):
        print(f"  ✅ DATABASE_PATH: {os.getenv('DATABASE_PATH')}")
    else:
        print("  ⚠️ DATABASE_PATH not set (will use local database)")
    
    if os.getenv('LOYVERSE_TOKEN'):
        print("  ✅ LOYVERSE_TOKEN: Set")
    else:
        print("  ⚠️ LOYVERSE_TOKEN not set (using default)")
    
    return True

def check_render_config():
    """Check Render deployment configuration"""
    print("\n🚀 Checking Render configuration...")
    
    try:
        with open('render.yaml', 'r') as f:
            content = f.read()
            
        required_configs = [
            'type: web',
            'env: python',
            'buildCommand:',
            'startCommand:',
            'LOYVERSE_TOKEN'
        ]
        
        for config in required_configs:
            if config in content:
                print(f"  ✅ {config}")
            else:
                print(f"  ❌ {config} - Missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Render config check failed: {e}")
        return False

def main():
    """Run all deployment checks"""
    print("🚀 Snow AI Dashboard - Deployment Verification\n")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Required Files", check_files),
        ("Database Functionality", check_database_functionality),
        ("Translation System", check_translations),
        ("Environment Variables", check_environment_variables),
        ("Render Configuration", check_render_config)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"  ❌ {check_name} check failed with error: {e}")
            results.append((check_name, False))
    
    print("\n" + "=" * 50)
    print("📋 DEPLOYMENT VERIFICATION SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL CHECKS PASSED - READY FOR DEPLOYMENT!")
        print("\n📋 Next Steps:")
        print("  1. Commit all changes to git")
        print("  2. Push to your repository")
        print("  3. Deploy to Render")
        print("  4. Monitor logs for any issues")
    else:
        print("⚠️ SOME CHECKS FAILED - FIX ISSUES BEFORE DEPLOYMENT")
        print("\n📋 Action Required:")
        print("  1. Fix the failed checks above")
        print("  2. Re-run this verification script")
        print("  3. Only deploy when all checks pass")
    
    print("\n🔗 Deployment Resources:")
    print("  • Render Dashboard: https://dashboard.render.com")
    print("  • App URL: Will be provided after deployment")
    print("  • Logs: Available in Render dashboard")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
