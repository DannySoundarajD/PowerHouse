#!/usr/bin/env python3
"""
Hardware Detection Script for Sentinel AI Workbench
Detects GPU, VRAM, system RAM, and recommends model tier configuration.
"""

import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple


def get_nvidia_gpu_info() -> Optional[Dict]:
    """Query NVIDIA GPU information using nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        
        lines = result.stdout.strip().split('\n')
        if not lines:
            return None
        
        # Parse first GPU (assume single GPU for MVP)
        parts = lines[0].split(',')
        if len(parts) < 2:
            return None
        
        return {
            "name": parts[0].strip(),
            "vram_mb": int(parts[1].strip()),
            "vram_gb": round(int(parts[1].strip()) / 1024, 1),
        }
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return None


def get_system_memory() -> Optional[float]:
    """Get total system RAM in GB."""
    try:
        import psutil
        return round(psutil.virtual_memory().total / (1024**3), 1)
    except ImportError:
        # Fallback: try reading from system (Windows only)
        try:
            result = subprocess.run(
                ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            # Parse output (format: "TotalPhysicalMemory\n<bytes>")
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                bytes_val = int(lines[1].strip())
                return round(bytes_val / (1024**3), 1)
        except Exception:
            pass
    return None


def recommend_model_tier(vram_gb: float, system_ram_gb: float) -> Tuple[str, Dict]:
    """Recommend model configuration tier based on hardware."""
    
    if vram_gb >= 20:
        tier = "high"
        models = {
            "router": "qwen3.5:4b",
            "reasoning": "deepseek-r1:32b",
            "coding": "qwen3-coder:30b",
            "vision": "qwen3-vl:30b",
        }
        notes = "High-end GPU: Can run full-size specialist models with excellent performance."
    
    elif vram_gb >= 8:
        tier = "medium"
        models = {
            "router": "qwen3.5:4b",
            "reasoning": "deepseek-r1:14b",
            "coding": "qwen2.5-coder:7b",
            "vision": "qwen3-vl:8b",
        }
        notes = "Mid-range GPU: Recommended configuration for most users. Can keep 2 models resident."
    
    elif vram_gb >= 4:
        tier = "low"
        models = {
            "router": "qwen3.5:2b",  # Safer default for 4GB
            "reasoning": "deepseek-r1:7b",
            "coding": "qwen2.5-coder:3b",
            "vision": "qwen3-vl:4b",
        }
        notes = "Entry-level GPU: Will use CPU offloading for larger models (slower but functional)."
    
    else:
        tier = "cpu-only"
        models = {
            "router": "qwen3.5:2b",
            "reasoning": "qwen3.5:2b",  # Fallback to router
            "coding": "qwen2.5-coder:3b",
            "vision": None,  # Vision requires GPU
        }
        notes = "No suitable GPU detected. Limited functionality; consider upgrading hardware."
    
    return tier, {
        "tier": tier,
        "models": models,
        "notes": notes,
    }


def check_ollama_installed() -> Dict:
    """Check if Ollama is installed and accessible."""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        version = result.stdout.strip()
        
        # Try to connect to Ollama API
        try:
            import httpx
            response = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5)
            if response.status_code == 200:
                api_status = "running"
                models = response.json().get("models", [])
                installed_models = [m["name"] for m in models]
            else:
                api_status = "not_running"
                installed_models = []
        except Exception:
            api_status = "not_accessible"
            installed_models = []
        
        return {
            "installed": True,
            "version": version,
            "api_status": api_status,
            "models": installed_models,
        }
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return {
            "installed": False,
            "version": None,
            "api_status": "not_installed",
            "models": [],
        }


def check_docker_installed() -> Dict:
    """Check if Docker is installed and running."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        version = result.stdout.strip()
        
        # Check if Docker daemon is running
        try:
            subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            daemon_status = "running"
        except subprocess.CalledProcessError:
            daemon_status = "not_running"
        
        return {
            "installed": True,
            "version": version,
            "daemon_status": daemon_status,
        }
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return {
            "installed": False,
            "version": None,
            "daemon_status": "not_installed",
        }


def main():
    """Main hardware detection routine."""
    print("=" * 70)
    print("Sentinel AI Workbench — Hardware Detection")
    print("=" * 70)
    print()
    
    # System info
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    print()
    
    # GPU detection
    print("🔍 Detecting GPU...")
    gpu_info = get_nvidia_gpu_info()
    if gpu_info:
        print(f"  ✓ GPU: {gpu_info['name']}")
        print(f"  ✓ VRAM: {gpu_info['vram_gb']} GB ({gpu_info['vram_mb']} MB)")
    else:
        print("  ⚠ No NVIDIA GPU detected (or nvidia-smi not accessible)")
        gpu_info = {"vram_gb": 0}
    print()
    
    # System RAM
    print("🔍 Detecting System Memory...")
    system_ram = get_system_memory()
    if system_ram:
        print(f"  ✓ Total RAM: {system_ram} GB")
    else:
        print("  ⚠ Could not detect system memory")
        system_ram = 8.0  # Assume minimum
    print()
    
    # Model tier recommendation
    print("📊 Recommended Model Configuration...")
    tier, config = recommend_model_tier(gpu_info["vram_gb"], system_ram)
    print(f"  Tier: {config['tier'].upper()}")
    print(f"  Router: {config['models']['router']}")
    print(f"  Reasoning: {config['models']['reasoning']}")
    print(f"  Coding: {config['models']['coding']}")
    print(f"  Vision: {config['models']['vision'] or 'N/A (requires GPU)'}")
    print(f"  Note: {config['notes']}")
    print()
    
    # Ollama check
    print("🔍 Checking Ollama...")
    ollama_info = check_ollama_installed()
    if ollama_info["installed"]:
        print(f"  ✓ Ollama installed: {ollama_info['version']}")
        print(f"  API status: {ollama_info['api_status']}")
        if ollama_info["models"]:
            print(f"  Installed models: {', '.join(ollama_info['models'][:5])}")
            if len(ollama_info["models"]) > 5:
                print(f"    ... and {len(ollama_info['models']) - 5} more")
        else:
            print("  ⚠ No models installed yet")
    else:
        print("  ✗ Ollama not installed")
        print("    Install from: https://ollama.com/download")
    print()
    
    # Docker check
    print("🔍 Checking Docker...")
    docker_info = check_docker_installed()
    if docker_info["installed"]:
        print(f"  ✓ Docker installed: {docker_info['version']}")
        if docker_info["daemon_status"] == "running":
            print("  ✓ Docker daemon is running")
        else:
            print("  ⚠ Docker daemon not running (start Docker Desktop)")
    else:
        print("  ✗ Docker not installed")
        print("    Install from: https://www.docker.com/products/docker-desktop/")
    print()
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    
    all_ready = (
        gpu_info["vram_gb"] >= 4 
        and ollama_info["installed"] 
        and ollama_info["api_status"] == "running"
        and docker_info["installed"]
        and docker_info["daemon_status"] == "running"
    )
    
    if all_ready:
        print("✅ System ready for Sentinel installation!")
        print()
        print("Next steps:")
        print("  1. Pull core models:")
        for model in config["models"].values():
            if model:
                print(f"     ollama pull {model}")
        print("  2. Run: python -m src.cli.app")
    else:
        print("⚠ System not fully ready. Please address the following:")
        if gpu_info["vram_gb"] < 4:
            print("  - GPU with 4GB+ VRAM recommended (detected: {:.1f}GB)".format(gpu_info["vram_gb"]))
        if not ollama_info["installed"]:
            print("  - Install Ollama: https://ollama.com/download")
        elif ollama_info["api_status"] != "running":
            print("  - Start Ollama service")
        if not docker_info["installed"]:
            print("  - Install Docker: https://www.docker.com/products/docker-desktop/")
        elif docker_info["daemon_status"] != "running":
            print("  - Start Docker Desktop")
    
    print()
    
    # Export JSON for programmatic use
    output = {
        "system": {
            "os": platform.system(),
            "release": platform.release(),
            "arch": platform.machine(),
        },
        "gpu": gpu_info,
        "ram_gb": system_ram,
        "tier": config,
        "ollama": ollama_info,
        "docker": docker_info,
        "ready": all_ready,
    }
    
    output_file = Path("data/hardware-info.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"Hardware info saved to: {output_file}")
    
    return 0 if all_ready else 1


if __name__ == "__main__":
    sys.exit(main())
