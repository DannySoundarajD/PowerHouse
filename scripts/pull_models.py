#!/usr/bin/env python3
"""
Model Pull Script for Sentinel AI Workbench
Downloads required models from Ollama registry with progress tracking.
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict


# Core models required for Sentinel (4GB VRAM tier)
CORE_MODELS = [
    {
        "tag": "qwen3.5:2b",
        "role": "router",
        "priority": 1,
        "size_gb": 2.7,
        "required": True,
    },
    {
        "tag": "qwen2.5-coder:3b",
        "role": "coding",
        "priority": 2,
        "size_gb": 1.9,
        "required": True,
    },
    {
        "tag": "deepseek-r1:7b",
        "role": "reasoning",
        "priority": 3,
        "size_gb": 4.7,
        "required": True,
    },
    {
        "tag": "qwen3-vl:4b",
        "role": "vision",
        "priority": 4,
        "size_gb": 3.3,
        "required": True,
    },
    {
        "tag": "nomic-embed-text",
        "role": "embedding",
        "priority": 5,
        "size_gb": 0.3,
        "required": True,
    },
]

# Optional upgrade models (for better hardware)
OPTIONAL_MODELS = [
    {"tag": "qwen3.5:4b", "role": "router", "size_gb": 3.4, "note": "Better router (if VRAM permits)"},
    {"tag": "qwen2.5-coder:7b", "role": "coding", "size_gb": 4.7, "note": "Better coding model (8GB+ VRAM)"},
    {"tag": "deepseek-r1:14b", "role": "reasoning", "size_gb": 9.5, "note": "Better reasoning (8GB+ VRAM)"},
]


def check_ollama_running() -> bool:
    """Check if Ollama API is accessible."""
    try:
        import httpx
        response = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def get_installed_models() -> List[str]:
    """Get list of already installed models."""
    try:
        import httpx
        response = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return [m["name"] for m in models]
    except Exception:
        pass
    return []


def pull_model(tag: str, role: str) -> bool:
    """Pull a model from Ollama registry with progress display."""
    print(f"\n{'='*70}")
    print(f"Pulling {tag} ({role})")
    print(f"{'='*70}")
    
    try:
        # Run ollama pull with real-time output
        process = subprocess.Popen(
            ["ollama", "pull", tag],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        
        for line in process.stdout:
            print(line, end='')
        
        process.wait()
        
        if process.returncode == 0:
            print(f"✓ Successfully pulled {tag}")
            return True
        else:
            print(f"✗ Failed to pull {tag} (exit code: {process.returncode})")
            return False
    
    except FileNotFoundError:
        print("✗ Error: ollama command not found. Please install Ollama first.")
        return False
    except KeyboardInterrupt:
        print("\n⚠ Pull interrupted by user")
        return False
    except Exception as e:
        print(f"✗ Error pulling {tag}: {e}")
        return False


def estimate_download_size(models: List[Dict]) -> float:
    """Estimate total download size in GB."""
    return sum(m["size_gb"] for m in models)


def main():
    """Main model pull routine."""
    print("=" * 70)
    print("Sentinel AI Workbench — Model Installer")
    print("=" * 70)
    print()
    
    # Check if Ollama is running
    if not check_ollama_running():
        print("✗ Ollama is not running!")
        print("  Please start Ollama and try again.")
        print("  - Windows: Ollama should auto-start after installation")
        print("  - Check: http://127.0.0.1:11434 in your browser")
        return 1
    
    print("✓ Ollama is running")
    print()
    
    # Check existing models
    print("🔍 Checking installed models...")
    installed = get_installed_models()
    if installed:
        print(f"  Found {len(installed)} installed models")
    else:
        print("  No models installed yet")
    print()
    
    # Filter models to install
    to_install = []
    skipped = []
    
    for model in CORE_MODELS:
        if model["tag"] in installed:
            print(f"  ⏭  Skipping {model['tag']} ({model['role']}) — already installed")
            skipped.append(model)
        else:
            to_install.append(model)
    
    if not to_install:
        print("\n✅ All core models are already installed!")
        print("\nOptional upgrades available:")
        for model in OPTIONAL_MODELS:
            if model["tag"] not in installed:
                print(f"  • {model['tag']} — {model['note']}")
        return 0
    
    # Show install plan
    print(f"\n📦 Installation Plan")
    print(f"{'='*70}")
    total_size = estimate_download_size(to_install)
    print(f"Models to install: {len(to_install)}")
    print(f"Estimated download size: ~{total_size:.1f} GB")
    print(f"Estimated time: ~{int(total_size * 2)} minutes (depends on internet speed)")
    print()
    
    for model in to_install:
        print(f"  {model['priority']}. {model['tag']:<25} ({model['role']:<10}) ~{model['size_gb']:.1f} GB")
    
    print()
    
    # Confirm
    try:
        response = input("Proceed with installation? [Y/n]: ").strip().lower()
        if response and response not in ['y', 'yes']:
            print("Installation cancelled.")
            return 0
    except KeyboardInterrupt:
        print("\nInstallation cancelled.")
        return 0
    
    # Pull models
    print()
    success_count = 0
    start_time = time.time()
    
    for model in sorted(to_install, key=lambda m: m["priority"]):
        if pull_model(model["tag"], model["role"]):
            success_count += 1
        else:
            if model["required"]:
                print(f"\n⚠ Warning: Failed to install required model {model['tag']}")
                response = input("Continue anyway? [y/N]: ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Installation aborted.")
                    return 1
    
    elapsed = time.time() - start_time
    
    # Summary
    print(f"\n{'='*70}")
    print("Installation Summary")
    print(f"{'='*70}")
    print(f"  Successfully installed: {success_count}/{len(to_install)} models")
    print(f"  Already installed: {len(skipped)} models")
    print(f"  Time elapsed: {int(elapsed // 60)} minutes {int(elapsed % 60)} seconds")
    print()
    
    if success_count == len(to_install):
        print("✅ All models installed successfully!")
        print()
        print("Next steps:")
        print("  1. Verify installation: ollama list")
        print("  2. Run Sentinel: python -m src.cli.app")
        return 0
    else:
        print("⚠ Some models failed to install.")
        print("  Check your internet connection and try again.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        sys.exit(130)
