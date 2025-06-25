"""
Compatibility fixes for the pickleball scheduling app.
Run this script to check versions and apply compatibility patches.
"""

import sys
import subprocess
import importlib
from packaging import version

def check_versions():
    """Check installed package versions and compatibility."""
    packages_to_check = {
        'httpx': '0.24.0',
        'fastapi': '0.100.0',
        'pydantic': '2.0.0',
        'websockets': '11.0.0',
        'google-genai': '0.1.0',  # Adjust based on actual package
    }
    
    print("Checking package versions...")
    for package, min_version in packages_to_check.items():
        try:
            pkg = importlib.import_module(package.replace('-', '_'))
            if hasattr(pkg, '__version__'):
                current_version = pkg.__version__
                print(f"{package}: {current_version}")
                
                if version.parse(current_version) < version.parse(min_version):
                    print(f"  ⚠️  {package} version {current_version} may be too old (minimum: {min_version})")
                else:
                    print(f"  ✅ {package} version is compatible")
            else:
                print(f"{package}: Version not available")
        except ImportError:
            print(f"❌ {package}: Not installed")
        except Exception as e:
            print(f"❌ {package}: Error checking version - {e}")

def apply_monkey_patches():
    """Apply monkey patches for compatibility issues."""
    print("\nApplying compatibility patches...")
    
    try:
        # Patch for extra_headers issue in websockets/httpx
        import asyncio
        import inspect
        
        # Get the original create_connection method
        original_create_connection = asyncio.BaseEventLoop.create_connection
        
        def patched_create_connection(self, protocol_factory, host=None, port=None, **kwargs):
            # Remove problematic extra_headers argument if present
            if 'extra_headers' in kwargs:
                print("Removing extra_headers from create_connection call")
                kwargs.pop('extra_headers')
            
            return original_create_connection(self, protocol_factory, host, port, **kwargs)
        
        # Apply the patch
        asyncio.BaseEventLoop.create_connection = patched_create_connection
        print("✅ Applied create_connection patch")
        
    except Exception as e:
        print(f"❌ Failed to apply create_connection patch: {e}")
    
    try:
        # Patch for Pydantic enum serialization warnings
        import warnings
        
        def custom_warning_handler(message, category, filename, lineno, file=None, line=None):
            # Suppress specific Pydantic serialization warnings
            if "PydanticSerializationUnexpectedValue" in str(message):
                return  # Suppress this warning
            
            # Show other warnings normally
            warnings._original_showwarning(message, category, filename, lineno, file, line)
        
        if not hasattr(warnings, '_original_showwarning'):
            warnings._original_showwarning = warnings.showwarning
            warnings.showwarning = custom_warning_handler
            print("✅ Applied Pydantic warning suppression")
        
    except Exception as e:
        print(f"❌ Failed to apply Pydantic patch: {e}")

def install_compatible_versions():
    """Install compatible versions of packages."""
    compatible_packages = [
        "httpx>=0.24.0,<0.26.0",
        "fastapi>=0.100.0,<0.105.0", 
        "pydantic>=2.0.0,<3.0.0",
        "websockets>=11.0.0,<12.0.0",
    ]
    
    print("\nInstalling compatible package versions...")
    for package in compatible_packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ Installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")

def create_compatibility_wrapper():
    """Create a compatibility wrapper module."""
    wrapper_code = '''
"""
Compatibility wrapper for the pickleball scheduling app.
Import this module at the beginning of your main.py to apply fixes.
"""

import warnings
import asyncio
from typing import Any

# Suppress Pydantic serialization warnings
def suppress_pydantic_warnings():
    warnings.filterwarnings("ignore", message=".*PydanticSerializationUnexpectedValue.*")

# Patch create_connection to handle extra_headers issue
def patch_create_connection():
    original_create_connection = asyncio.BaseEventLoop.create_connection
    
    async def patched_create_connection(self, protocol_factory, host=None, port=None, **kwargs):
        # Remove extra_headers if present
        kwargs.pop('extra_headers', None)
        return await original_create_connection(self, protocol_factory, host, port, **kwargs)
    
    asyncio.BaseEventLoop.create_connection = patched_create_connection

# Apply all patches
def apply_all_patches():
    suppress_pydantic_warnings()
    patch_create_connection()
    print("🔧 Applied compatibility patches")

# Auto-apply patches when imported
apply_all_patches()
'''
    
    try:
        with open('compatibility_wrapper.py', 'w') as f:
            f.write(wrapper_code)
        print("✅ Created compatibility_wrapper.py")
        print("   Add 'import compatibility_wrapper' at the top of your main.py")
    except Exception as e:
        print(f"❌ Failed to create compatibility wrapper: {e}")

if __name__ == "__main__":
    print("🔧 Pickleball App Compatibility Fixer")
    print("=" * 40)
    
    check_versions()
    apply_monkey_patches()
    create_compatibility_wrapper()
    
    print("\n" + "=" * 40)
    print("✅ Compatibility fixes applied!")
    print("\nRecommended next steps:")
    print("1. Restart your application")
    print("2. If issues persist, run: pip install --upgrade httpx fastapi pydantic")
    print("3. Consider using a virtual environment for better dependency management")