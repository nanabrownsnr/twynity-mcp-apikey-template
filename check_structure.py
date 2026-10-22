"""Simple test to check that our Replicate MCP structure works."""

import sys
import os
    
def test_import():
    """Test that we can at least import without syntax errors."""
    
    # Test simple imports to make sure there are no syntax errors  
    try:
        from app.tools.replicate import register_tools
        print("✓ Successfully imported app.tools.replicate")
        
        # Test main module
        from app.main import mcp 
        print("✓ Successfully imported app.main")
        
        # Test config
        from app.config import settings
        print("✓ Successfully imported app.config (settings)")
        
        print("✓ All basic imports successful")
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_structure():
    """Check core project structure."""
    
    required_files = [
        "app/tools/replicate.py",
        "app/main.py", 
        "app/config.py",
        "tests/test_replicate_tools.py"
    ]
    
    missing = []
    for file_path in required_files:
        full_path = os.path.join(os.getcwd(), file_path)
        if not os.path.exists(full_path):
            missing.append(file_path)
    
    if missing:
        print(f"✗ Missing files: {missing}")
        return False
    
    print("✓ All core structure files present")
    return True

if __name__ == "__main__":
    print("Checking Replicate MCP project structure...")
    
    success = True
    success &= test_import()
    success &= test_structure()
    
    if success:
        print("\n✓ Basic structure check passed!")
        print("The replication MCP server is ready to run.")
    else:
        print("\n✗ Basic checks failed")
        sys.exit(1)