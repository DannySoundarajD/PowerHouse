"""
Build Windows installer for Sentinel AI Workbench using PyInstaller.

Creates standalone executable with TUI installer for dependency checking.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
INSTALLER_DIR = PROJECT_ROOT / "installer"


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__} found")
        return True
    except ImportError:
        print("✗ PyInstaller not found")
        print("  Install with: pip install pyinstaller")
        return False


def clean_build_dirs():
    """Clean previous build artifacts."""
    print("\n[1/5] Cleaning build directories...")
    
    for directory in [BUILD_DIR, DIST_DIR]:
        if directory.exists():
            print(f"  Removing {directory}")
            shutil.rmtree(directory)
    
    print("✓ Build directories cleaned")


def create_spec_file():
    """Create PyInstaller spec file."""
    print("\n[2/5] Creating PyInstaller spec file...")
    
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# Project root
project_root = Path(SPECPATH)

# All Python source files
a = Analysis(
    ['src/cli/app.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ('models/*.yaml', 'models'),
        ('docker/*.Dockerfile', 'docker'),
        ('.env.example', '.'),
        ('README.md', '.'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'textual',
        'rich',
        'ollama',
        'chromadb',
        'docker',
        'psutil',
        'pytesseract',
        'pdf2image',
        'PIL',
        'pandas',
        'openpyxl',
        'docx',
        'pptx',
        'pdfplumber',
        'PyPDF2',
        'sqlalchemy',
        'sentence_transformers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='sentinel-ai',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='sentinel-ai',
)
"""
    
    spec_path = PROJECT_ROOT / "sentinel-ai.spec"
    spec_path.write_text(spec_content)
    
    print(f"✓ Created spec file: {spec_path}")
    return spec_path


def build_executable(spec_path: Path):
    """Build executable with PyInstaller."""
    print("\n[3/5] Building executable with PyInstaller...")
    print("  This may take several minutes...")
    
    try:
        subprocess.run(
            ["pyinstaller", "--clean", str(spec_path)],
            cwd=PROJECT_ROOT,
            check=True
        )
        print("✓ Executable built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Build failed: {e}")
        return False


def create_installer_script():
    """Create TUI installer script."""
    print("\n[4/5] Creating installer script...")
    
    installer_content = '''"""
Sentinel AI Workbench - TUI Installer
Checks dependencies and sets up the environment.
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


class Color:
    """ANSI color codes."""
    GREEN = "\\033[92m"
    YELLOW = "\\033[93m"
    RED = "\\033[91m"
    BLUE = "\\033[94m"
    BOLD = "\\033[1m"
    RESET = "\\033[0m"


def print_header():
    """Print installer header."""
    print(f"{Color.BOLD}{Color.BLUE}")
    print("=" * 60)
    print("  Sentinel AI Workbench - Installation Wizard")
    print("  Sovereign On-Premise AI for Air-Gapped Environments")
    print("=" * 60)
    print(f"{Color.RESET}\\n")


def check_python():
    """Check Python version."""
    print(f"{Color.BOLD}[1/6] Checking Python...{Color.RESET}")
    
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"  {Color.GREEN}✓ Python {version.major}.{version.minor}.{version.micro}{Color.RESET}")
        return True
    else:
        print(f"  {Color.RED}✗ Python 3.11+ required (found {version.major}.{version.minor}){Color.RESET}")
        return False


def check_ollama():
    """Check if Ollama is installed."""
    print(f"\\n{Color.BOLD}[2/6] Checking Ollama...{Color.RESET}")
    
    if shutil.which("ollama"):
        print(f"  {Color.GREEN}✓ Ollama found{Color.RESET}")
        
        # Check if running
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"  {Color.GREEN}✓ Ollama is running{Color.RESET}")
                return True
            else:
                print(f"  {Color.YELLOW}⚠ Ollama not running. Start with: ollama serve{Color.RESET}")
                return False
        except Exception:
            print(f"  {Color.YELLOW}⚠ Ollama not running{Color.RESET}")
            return False
    else:
        print(f"  {Color.RED}✗ Ollama not found{Color.RESET}")
        print(f"  {Color.YELLOW}  Install from: https://ollama.ai{Color.RESET}")
        return False


def check_docker():
    """Check if Docker is installed."""
    print(f"\\n{Color.BOLD}[3/6] Checking Docker...{Color.RESET}")
    
    if shutil.which("docker"):
        print(f"  {Color.GREEN}✓ Docker found{Color.RESET}")
        
        # Check if running
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"  {Color.GREEN}✓ Docker is running{Color.RESET}")
                return True
            else:
                print(f"  {Color.YELLOW}⚠ Docker not running{Color.RESET}")
                return False
        except Exception:
            print(f"  {Color.YELLOW}⚠ Docker not running{Color.RESET}")
            return False
    else:
        print(f"  {Color.RED}✗ Docker not found{Color.RESET}")
        print(f"  {Color.YELLOW}  Install from: https://docker.com{Color.RESET}")
        return False


def check_gpu():
    """Check GPU availability."""
    print(f"\\n{Color.BOLD}[4/6] Checking GPU...{Color.RESET}")
    
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"  {Color.GREEN}✓ CUDA GPU detected: {gpu_name}{Color.RESET}")
            return True
    except ImportError:
        pass
    
    # Fallback: check via nvidia-smi
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                gpu_name = result.stdout.strip()
                print(f"  {Color.GREEN}✓ NVIDIA GPU detected: {gpu_name}{Color.RESET}")
                return True
        except Exception:
            pass
    
    print(f"  {Color.YELLOW}⚠ No GPU detected (CPU mode will be used){Color.RESET}")
    return False


def check_tesseract():
    """Check if Tesseract OCR is installed."""
    print(f"\\n{Color.BOLD}[5/6] Checking Tesseract OCR...{Color.RESET}")
    
    if shutil.which("tesseract"):
        print(f"  {Color.GREEN}✓ Tesseract found{Color.RESET}")
        return True
    else:
        print(f"  {Color.YELLOW}⚠ Tesseract not found (OCR will not work){Color.RESET}")
        print(f"  {Color.YELLOW}  Install from: https://github.com/UB-Mannheim/tesseract/wiki{Color.RESET}")
        return False


def check_poppler():
    """Check if Poppler is installed (for PDF processing)."""
    print(f"\\n{Color.BOLD}[6/6] Checking Poppler...{Color.RESET}")
    
    if shutil.which("pdftoppm"):
        print(f"  {Color.GREEN}✓ Poppler found{Color.RESET}")
        return True
    else:
        print(f"  {Color.YELLOW}⚠ Poppler not found (PDF processing will not work){Color.RESET}")
        print(f"  {Color.YELLOW}  Download from: https://github.com/oschwartz10612/poppler-windows/releases{Color.RESET}")
        return False


def create_shortcuts():
    """Create desktop and start menu shortcuts."""
    if platform.system() != "Windows":
        return
    
    print(f"\\n{Color.BOLD}Creating shortcuts...{Color.RESET}")
    
    # This would use pywin32 to create shortcuts
    # Simplified for now
    print(f"  {Color.YELLOW}⚠ Manual shortcut creation required{Color.RESET}")


def main():
    """Run installation checks."""
    print_header()
    
    checks = [
        ("Python", check_python(), True),
        ("Ollama", check_ollama(), True),
        ("Docker", check_docker(), True),
        ("GPU", check_gpu(), False),
        ("Tesseract", check_tesseract(), False),
        ("Poppler", check_poppler(), False),
    ]
    
    print(f"\\n{Color.BOLD}{'=' * 60}{Color.RESET}")
    print(f"{Color.BOLD}Installation Summary{Color.RESET}\\n")
    
    required_passed = all(passed for _, passed, required in checks if required)
    
    for name, passed, required in checks:
        status = f"{Color.GREEN}✓" if passed else f"{Color.RED}✗" if required else f"{Color.YELLOW}⚠"
        req_text = "(required)" if required else "(optional)"
        print(f"  {status} {name:15} {req_text}{Color.RESET}")
    
    print(f"\\n{Color.BOLD}{'=' * 60}{Color.RESET}\\n")
    
    if required_passed:
        print(f"{Color.GREEN}{Color.BOLD}✓ All required dependencies met!{Color.RESET}")
        print(f"\\n{Color.BOLD}To start Sentinel AI:{Color.RESET}")
        print(f"  {Color.BLUE}sentinel-ai{Color.RESET}")
        return 0
    else:
        print(f"{Color.RED}{Color.BOLD}✗ Missing required dependencies{Color.RESET}")
        print(f"\\nPlease install missing dependencies and run installer again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
'''
    
    INSTALLER_DIR.mkdir(exist_ok=True)
    installer_path = INSTALLER_DIR / "install.py"
    installer_path.write_text(installer_content)
    
    print(f"✓ Created installer: {installer_path}")


def create_batch_scripts():
    """Create convenience batch scripts."""
    print("\n[5/5] Creating batch scripts...")
    
    # Launcher script
    launcher_content = """@echo off
REM Sentinel AI Workbench Launcher

echo Starting Sentinel AI Workbench...
cd /d "%~dp0"

REM Check if Ollama is running
ollama list >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Ollama is not running
    echo Start Ollama first with: ollama serve
    pause
    exit /b 1
)

REM Launch Sentinel
sentinel-ai.exe

pause
"""
    
    launcher_path = DIST_DIR / "sentinel-ai" / "launch.bat"
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text(launcher_content)
    
    # Installer script
    install_bat_content = """@echo off
REM Run Sentinel AI Installation Wizard

cd /d "%~dp0"
python installer\\install.py
pause
"""
    
    install_bat_path = DIST_DIR / "sentinel-ai" / "install.bat"
    install_bat_path.write_text(install_bat_content)
    
    print(f"✓ Created launch.bat")
    print(f"✓ Created install.bat")


def main():
    """Main build process."""
    parser = argparse.ArgumentParser(description="Build Sentinel AI Windows installer")
    parser.add_argument("--skip-clean", action="store_true", help="Skip cleaning build directories")
    args = parser.parse_args()
    
    print("=" * 60)
    print("  Sentinel AI Workbench - Build Script")
    print("=" * 60)
    
    # Check PyInstaller
    if not check_pyinstaller():
        return 1
    
    # Clean
    if not args.skip_clean:
        clean_build_dirs()
    
    # Create spec
    spec_path = create_spec_file()
    
    # Build
    if not build_executable(spec_path):
        return 1
    
    # Create installer
    create_installer_script()
    
    # Create batch scripts
    create_batch_scripts()
    
    print("\n" + "=" * 60)
    print("  Build Complete!")
    print("=" * 60)
    print(f"\nExecutable location: {DIST_DIR / 'sentinel-ai'}")
    print("\nNext steps:")
    print("  1. Copy the dist/sentinel-ai folder to target machine")
    print("  2. Run install.bat to check dependencies")
    print("  3. Run sentinel-ai.exe or launch.bat to start")
    print("\n" + "=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
