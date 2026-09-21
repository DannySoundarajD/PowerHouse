#!/usr/bin/env python3
"""
Build Docker sandbox images for Sentinel AI Workbench.
"""

import subprocess
import sys
from pathlib import Path


IMAGES = [
    {
        "name": "sentinel-sandbox-python",
        "dockerfile": "docker/sandbox-python.Dockerfile",
        "description": "Python 3.11 sandbox environment",
    },
    {
        "name": "sentinel-sandbox-node",
        "dockerfile": "docker/sandbox-node.Dockerfile",
        "description": "Node.js 18 sandbox environment",
    },
    {
        "name": "sentinel-sandbox-shell",
        "dockerfile": "docker/sandbox-shell.Dockerfile",
        "description": "Shell/Bash sandbox environment",
    },
]


def check_docker():
    """Check if Docker is available."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        print(f"✓ {result.stdout.strip()}")
        return True
    except Exception as e:
        print(f"✗ Docker not available: {e}")
        return False


def build_image(name: str, dockerfile: str, description: str) -> bool:
    """Build a Docker image."""
    print(f"\n{'='*70}")
    print(f"Building: {name}")
    print(f"Description: {description}")
    print(f"Dockerfile: {dockerfile}")
    print(f"{'='*70}")
    
    # Check if Dockerfile exists
    if not Path(dockerfile).exists():
        print(f"✗ Dockerfile not found: {dockerfile}")
        return False
    
    try:
        # Build image
        cmd = [
            "docker", "build",
            "-t", f"{name}:latest",
            "-f", dockerfile,
            ".",
        ]
        
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=False,  # Show output in real-time
            text=True,
            check=True,
        )
        
        print(f"\n✓ Successfully built {name}:latest")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed to build {name}: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Error building {name}: {e}")
        return False


def main():
    """Main build routine."""
    print("=" * 70)
    print("Sentinel AI Workbench — Sandbox Image Builder")
    print("=" * 70)
    print()
    
    # Check Docker
    if not check_docker():
        print("\n✗ Please install Docker Desktop and ensure it's running.")
        return 1
    
    print()
    
    # Build images
    success_count = 0
    failed = []
    
    for image in IMAGES:
        if build_image(image["name"], image["dockerfile"], image["description"]):
            success_count += 1
        else:
            failed.append(image["name"])
    
    # Summary
    print(f"\n{'='*70}")
    print("Build Summary")
    print(f"{'='*70}")
    print(f"  Successfully built: {success_count}/{len(IMAGES)}")
    
    if failed:
        print(f"  Failed: {', '.join(failed)}")
    
    print()
    
    if success_count == len(IMAGES):
        print("✅ All sandbox images built successfully!")
        print()
        print("Next steps:")
        print("  1. Verify images: docker images | grep sentinel-sandbox")
        print("  2. Test execution: python -m src.cli.app")
        print("  3. Try code execution in the chat")
        return 0
    else:
        print("⚠ Some images failed to build.")
        print("  Check Docker is running and Dockerfiles are valid.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
