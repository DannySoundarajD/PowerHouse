"""
Sandboxed code execution tool for Sentinel AI Workbench.
Executes code in isolated Docker containers with resource limits and no network access.
"""

import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import docker
    from docker.errors import DockerException, ImageNotFound, ContainerError
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

from .base import Tool
from ..utils.constants import (
    SANDBOX_MEMORY_LIMIT,
    SANDBOX_CPU_LIMIT,
    SANDBOX_TIMEOUT,
    SANDBOX_NETWORK_MODE,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SandboxExecTool(Tool):
    """
    Tool for executing code in sandboxed Docker containers.
    Supports Python, JavaScript/Node.js, and Shell scripts.
    """
    
    # Sandbox images (must be built first)
    SANDBOX_IMAGES = {
        "python": "sentinel-sandbox-python:latest",
        "javascript": "sentinel-sandbox-node:latest",
        "node": "sentinel-sandbox-node:latest",
        "shell": "sentinel-sandbox-shell:latest",
        "bash": "sentinel-sandbox-shell:latest",
    }
    
    def __init__(self):
        """Initialize sandbox executor."""
        self.docker_available = DOCKER_AVAILABLE
        self.client = None
        
        if DOCKER_AVAILABLE:
            try:
                self.client = docker.from_env()
                # Test connection
                self.client.ping()
                logger.info("Docker client initialized successfully")
            except Exception as e:
                logger.warning(f"Docker not available: {e}")
                self.docker_available = False
                self.client = None
        else:
            logger.warning("Docker SDK not installed, sandbox execution disabled")
    
    @property
    def name(self) -> str:
        return "execute_code"
    
    @property
    def description(self) -> str:
        return "Execute code in a sandboxed Docker container. Supports Python, JavaScript/Node.js, and Shell scripts. No network access, resource-limited."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "enum": ["python", "javascript", "node", "shell", "bash"],
                    "description": "Programming language"
                },
                "code": {
                    "type": "string",
                    "description": "Code to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Execution timeout in seconds (default: {SANDBOX_TIMEOUT})",
                    "default": SANDBOX_TIMEOUT
                },
            },
            "required": ["language", "code"]
        }
    
    def _get_sandbox_image(self, language: str) -> Optional[str]:
        """Get Docker image name for language."""
        return self.SANDBOX_IMAGES.get(language.lower())
    
    def _prepare_code_file(self, language: str, code: str, workdir: Path) -> Path:
        """
        Prepare code file in temporary directory.
        
        Returns:
            Path to code file
        """
        extensions = {
            "python": ".py",
            "javascript": ".js",
            "node": ".js",
            "shell": ".sh",
            "bash": ".sh",
        }
        
        ext = extensions.get(language.lower(), ".txt")
        code_file = workdir / f"code{ext}"
        code_file.write_text(code, encoding='utf-8')
        
        return code_file
    
    def _get_run_command(self, language: str, code_file_name: str) -> list:
        """Get command to run code in container."""
        commands = {
            "python": ["python", f"/workspace/{code_file_name}"],
            "javascript": ["node", f"/workspace/{code_file_name}"],
            "node": ["node", f"/workspace/{code_file_name}"],
            "shell": ["bash", f"/workspace/{code_file_name}"],
            "bash": ["bash", f"/workspace/{code_file_name}"],
        }
        
        return commands.get(language.lower(), [])
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute code in sandbox."""
        if not self.docker_available:
            return {
                "status": "error",
                "error": "Docker not available. Please ensure Docker Desktop is running.",
            }
        
        language = kwargs.get("language", "").lower()
        code = kwargs.get("code", "")
        timeout = kwargs.get("timeout", SANDBOX_TIMEOUT)
        
        # Validate language
        if language not in self.SANDBOX_IMAGES:
            return {
                "status": "error",
                "error": f"Unsupported language: {language}. Supported: {', '.join(self.SANDBOX_IMAGES.keys())}"
            }
        
        # Get sandbox image
        image = self._get_sandbox_image(language)
        
        # Check if image exists
        try:
            self.client.images.get(image)
        except ImageNotFound:
            return {
                "status": "error",
                "error": f"Sandbox image not found: {image}. Please build sandbox images first.",
            }
        
        # Create temporary workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            
            try:
                # Prepare code file
                code_file = self._prepare_code_file(language, code, workdir)
                logger.info(f"Executing {language} code in sandbox (timeout={timeout}s)")
                
                # Get run command
                command = self._get_run_command(language, code_file.name)
                
                # Run container
                start_time = time.time()
                
                container = self.client.containers.run(
                    image=image,
                    command=command,
                    volumes={str(workdir): {"bind": "/workspace", "mode": "rw"}},
                    working_dir="/workspace",
                    network_mode=SANDBOX_NETWORK_MODE,  # No network access
                    mem_limit=SANDBOX_MEMORY_LIMIT,
                    # CPU limit: convert to CPU quota (1.5 CPUs = 150000 microseconds per 100ms)
                    cpu_quota=int(SANDBOX_CPU_LIMIT * 100000),
                    cpu_period=100000,
                    read_only=False,  # Allow writes to /workspace
                    tmpfs={"/tmp": "size=512m"},
                    detach=True,
                    remove=False,  # We'll remove manually after getting logs
                    user="1000:1000",  # Run as non-root
                )
                
                # Wait for completion
                try:
                    result = container.wait(timeout=timeout)
                    exit_code = result.get("StatusCode", -1)
                except Exception as timeout_error:
                    # Timeout occurred
                    container.kill()
                    elapsed = time.time() - start_time
                    
                    return {
                        "status": "error",
                        "error": f"Execution timeout after {elapsed:.1f}s",
                        "output": "Execution was terminated due to timeout.",
                    }
                
                # Get logs
                logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='replace')
                
                # Clean up container
                try:
                    container.remove()
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")
                
                elapsed = time.time() - start_time
                
                # Check for network access attempts (shouldn't happen with --network=none)
                if "connection refused" in logs.lower() or "network" in logs.lower():
                    logger.warning(f"Possible network access attempt in sandbox")
                
                # Determine success/failure
                if exit_code == 0:
                    status = "success"
                    logger.info(f"Sandbox execution successful ({elapsed:.2f}s)")
                else:
                    status = "error"
                    logger.warning(f"Sandbox execution failed with exit code {exit_code}")
                
                return {
                    "status": status,
                    "output": logs,
                    "metadata": {
                        "language": language,
                        "exit_code": exit_code,
                        "execution_time": round(elapsed, 2),
                        "timeout": timeout,
                    }
                }
            
            except ContainerError as e:
                return {
                    "status": "error",
                    "error": f"Container execution error: {e}",
                    "output": str(e),
                }
            
            except Exception as e:
                logger.error(f"Sandbox execution failed: {e}", exc_info=True)
                return {
                    "status": "error",
                    "error": str(e),
                }
    
    def check_docker_status(self) -> Dict[str, Any]:
        """Check if Docker is available and ready."""
        if not DOCKER_AVAILABLE:
            return {
                "available": False,
                "error": "Docker SDK not installed (pip install docker)"
            }
        
        if not self.client:
            return {
                "available": False,
                "error": "Docker client not initialized. Is Docker Desktop running?"
            }
        
        try:
            self.client.ping()
            
            # Check for sandbox images
            images_status = {}
            for lang, image in self.SANDBOX_IMAGES.items():
                try:
                    self.client.images.get(image)
                    images_status[lang] = "available"
                except ImageNotFound:
                    images_status[lang] = "not_built"
            
            return {
                "available": True,
                "images": images_status,
            }
        
        except DockerException as e:
            return {
                "available": False,
                "error": f"Docker daemon not running: {e}"
            }
