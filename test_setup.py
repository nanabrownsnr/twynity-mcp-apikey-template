"""Run basic tests for Replicate MCP server."""

import sys
import os

# Add the project root to Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that our module can be imported properly."""
    # Import modules we created to make sure they don't have syntax errors
    try:
        from app.tools.replicate import register_tools
        from app.main import mcp
        print("✓ All core modules imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_structure():
    """Test that the project structure is correct."""
    dirs = [
        "app/tools",
        "app/ui/replicate",
        "app/connection_store.py",
        "app/main.py",
        "app/config.py",
        "tests/test_replicate_tools.py"
    ]
    
    missing = []
    for dir_path in dirs:
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), dir_path)
        if not os.path.exists(full_path):
            missing.append(dir_path)
    
    if missing:
        print(f"✗ Missing directories/files: {missing}")
        return False
    
    print("✓ Project structure looks correct")
    return True

if __name__ == "__main__":
    print("Running basic checks for Replicate MCP server...")
    success = True
    success &= test_imports()
    success &= test_structure()
    
    if success:
        print("✓ All checks passed!")
    else:
        print("✗ Some checks failed")
        sys.exit(1)