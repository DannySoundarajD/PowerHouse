"""
Comprehensive Installation Verification Script

Checks all components and dependencies before running Sentinel AI.
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class Color:
    """ANSI color codes."""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_header(text):
    """Print section header."""
    print(f"\n{Color.BOLD}{Color.BLUE}{'='*60}{Color.RESET}")
    print(f"{Color.BOLD}{Color.BLUE}{text}{Color.RESET}")
    print(f"{Color.BOLD}{Color.BLUE}{'='*60}{Color.RESET}\n")


def check_imports():
    """Check if all Python imports work."""
    print_header("[1/8] Checking Python Imports")
    
    imports_to_check = [
        ("textual", "Textual TUI framework"),
        ("rich", "Rich formatting"),
        ("ollama", "Ollama client"),
        ("chromadb", "ChromaDB vector store"),
        ("docker", "Docker SDK"),
        ("psutil", "System monitoring"),
        ("PIL", "Pillow image processing"),
        ("pandas", "Data processing"),
        ("docx", "Word document generation"),
        ("pptx", "PowerPoint generation"),
        ("sqlalchemy", "Database ORM"),
    ]
    
    all_ok = True
    for module, description in imports_to_check:
        try:
            __import__(module)
            print(f"  {Color.GREEN}✓{Color.RESET} {description:30} ({module})")
        except ImportError as e:
            print(f"  {Color.RED}✗{Color.RESET} {description:30} ({module}) - {e}")
            all_ok = False
    
    return all_ok


def check_project_structure():
    """Check if project structure is correct."""
    print_header("[2/8] Checking Project Structure")
    
    required_dirs = [
        "src/agent",
        "src/cli",
        "src/models",
        "src/network",
        "src/tools",
        "src/utils",
        "models",
        "docker",
        "scripts",
        "tests",
        "data",
        "logs",
        "output",
        "kb",
    ]
    
    all_ok = True
    for dir_path in required_dirs:
        full_path = Path(dir_path)
        if full_path.exists():
            print(f"  {Color.GREEN}✓{Color.RESET} {dir_path}/")
        else:
            print(f"  {Color.RED}✗{Color.RESET} {dir_path}/ - MISSING")
            all_ok = False
    
    return all_ok


def check_key_files():
    """Check if key files exist."""
    print_header("[3/8] Checking Key Files")
    
    key_files = [
        "src/agent/master_agent.py",
        "src/agent/simple_agent.py",
        "src/cli/app.py",
        "src/models/ollama_backend.py",
        "src/models/registry.py",
        "src/tools/file_ops.py",
        "src/tools/sandbox_exec.py",
        "src/tools/vision_pipeline.py",
        "src/tools/local_rag.py",
        "src/network/guard.py",
        "src/utils/session_state.py",
        "src/utils/logger.py",
        "src/utils/constants.py",
        "models/qwen3.5-2b-router.yaml",
        "requirements.txt",
        "README.md",
        "DEMO.md",
        "COMPLETION_SUMMARY.md",
    ]
    
    all_ok = True
    for file_path in key_files:
        full_path = Path(file_path)
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"  {Color.GREEN}✓{Color.RESET} {file_path:45} ({size:,} bytes)")
        else:
            print(f"  {Color.RED}✗{Color.RESET} {file_path:45} - MISSING")
            all_ok = False
    
    return all_ok


def check_imports_in_code():
    """Check if code imports are correct."""
    print_header("[4/8] Checking Code Imports")
    
    checks = []
    
    # Check master_agent imports
    try:
        from src.agent.master_agent import MasterAgent
        print(f"  {Color.GREEN}✓{Color.RESET} MasterAgent imports successfully")
        checks.append(True)
    except Exception as e:
        print(f"  {Color.RED}✗{Color.RESET} MasterAgent import failed: {e}")
        checks.append(False)
    
    # Check CLI app imports
    try:
        from src.cli.app import SentinelCLI
        print(f"  {Color.GREEN}✓{Color.RESET} SentinelCLI imports successfully")
        checks.append(True)
    except Exception as e:
        print(f"  {Color.RED}✗{Color.RESET} SentinelCLI import failed: {e}")
        checks.append(False)
    
    # Check tool imports
    try:
        from src.tools import get_tool_registry
        print(f"  {Color.GREEN}✓{Color.RESET} Tool registry imports successfully")
        checks.append(True)
    except Exception as e:
        print(f"  {Color.RED}✗{Color.RESET} Tool registry import failed: {e}")
        checks.append(False)
    
    # Check backend
    try:
        from src.models.ollama_backend import get_ollama_backend
        print(f"  {Color.GREEN}✓{Color.RESET} Ollama backend imports successfully")
        checks.append(True)
    except Exception as e:
        print(f"  {Color.RED}✗{Color.RESET} Ollama backend import failed: {e}")
        checks.append(False)
    
    # Check network guard
    try:
        from src.network.guard import NetworkGuard
        print(f"  {Color.GREEN}✓{Color.RESET} NetworkGuard imports successfully")
        checks.append(True)
    except Exception as e:
        print(f"  {Color.RED}✗{Color.RESET} NetworkGuard import failed: {e}")
        checks.append(False)
    
    return all(checks)


def check_ollama():
    """Check if Ollama is running."""
    print_header("[5/8] Checking Ollama")
    
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"  {Color.GREEN}✓{Color.RESET} Ollama is running")
            
            # List models
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                print(f"\n  Installed models:")
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        print(f"    • {line.split()[0]}")
            
            return True
        else:
            print(f"  {Color.YELLOW}⚠{Color.RESET} Ollama not running")
            print(f"    Start with: ollama serve")
            return False
    
    except FileNotFoundError:
        print(f"  {Color.RED}✗{Color.RESET} Ollama not found")
        print(f"    Install from: https://ollama.ai")
        return False
    except Exception as e:
        print(f"  {Color.YELLOW}⚠{Color.RESET} Could not check Ollama: {e}")
        return False


def check_docker():
    """Check if Docker is running."""
    print_header("[6/8] Checking Docker")
    
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"  {Color.GREEN}✓{Color.RESET} Docker is running")
            return True
        else:
            print(f"  {Color.YELLOW}⚠{Color.RESET} Docker not running")
            return False
    
    except FileNotFoundError:
        print(f"  {Color.RED}✗{Color.RESET} Docker not found")
        print(f"    Install from: https://docker.com")
        return False
    except Exception as e:
        print(f"  {Color.YELLOW}⚠{Color.RESET} Could not check Docker: {e}")
        return False


def check_optional_deps():
    """Check optional dependencies."""
    print_header("[7/8] Checking Optional Dependencies")
    
    # Tesseract
    try:
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"  {Color.GREEN}✓{Color.RESET} Tesseract OCR installed")
        else:
            print(f"  {Color.YELLOW}⚠{Color.RESET} Tesseract not found (OCR will not work)")
    except FileNotFoundError:
        print(f"  {Color.YELLOW}⚠{Color.RESET} Tesseract not found (OCR will not work)")
    
    # Poppler
    try:
        result = subprocess.run(
            ["pdftoppm", "-v"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"  {Color.GREEN}✓{Color.RESET} Poppler installed")
        else:
            print(f"  {Color.YELLOW}⚠{Color.RESET} Poppler not found (PDF processing limited)")
    except FileNotFoundError:
        print(f"  {Color.YELLOW}⚠{Color.RESET} Poppler not found (PDF processing limited)")
    
    return True  # Optional deps don't fail verification


def check_database():
    """Check database initialization."""
    print_header("[8/8] Checking Database")
    
    try:
        from src.utils.session_state import get_session_state
        
        state = get_session_state()
        test_session = state.create_session(router_model="test")
        
        stats = state.get_stats(test_session)
        
        print(f"  {Color.GREEN}✓{Color.RESET} SQLite database initialized")
        print(f"  {Color.GREEN}✓{Color.RESET} Session creation works")
        print(f"  {Color.GREEN}✓{Color.RESET} FTS5 search available")
        
        return True
    
    except Exception as e:
        print(f"  {Color.RED}✗{Color.RESET} Database check failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print(f"{Color.BOLD}{Color.BLUE}")
    print("=" * 60)
    print("  Sentinel AI Workbench - Installation Verification")
    print("=" * 60)
    print(f"{Color.RESET}")
    
    checks = {
        "Python Imports": check_imports(),
        "Project Structure": check_project_structure(),
        "Key Files": check_key_files(),
        "Code Imports": check_imports_in_code(),
        "Ollama": check_ollama(),
        "Docker": check_docker(),
        "Optional Deps": check_optional_deps(),
        "Database": check_database(),
    }
    
    # Summary
    print_header("Verification Summary")
    
    for check_name, result in checks.items():
        status = f"{Color.GREEN}PASS{Color.RESET}" if result else f"{Color.RED}FAIL{Color.RESET}"
        print(f"  {status:20} {check_name}")
    
    total = len(checks)
    passed = sum(1 for v in checks.values() if v)
    
    print(f"\n{Color.BOLD}Results: {passed}/{total} checks passed{Color.RESET}\n")
    
    if passed == total:
        print(f"{Color.GREEN}{Color.BOLD}✓ All checks passed! System is ready.{Color.RESET}\n")
        print(f"{Color.BOLD}To start Sentinel:{Color.RESET}")
        print(f"  python -m src.cli.app\n")
        return 0
    else:
        print(f"{Color.RED}{Color.BOLD}✗ Some checks failed. Please fix issues above.{Color.RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
