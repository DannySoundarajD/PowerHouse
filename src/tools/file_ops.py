"""
File operations tool for Sentinel AI Workbench.
Safe file read/write/list operations with path validation.
"""

import os
from pathlib import Path
from typing import Any, Dict

from .base import Tool
from ..utils.constants import ROOT_DIR, OUTPUT_DIR, KB_DIR, USER_ACCESSIBLE_DIRS
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FileOpsTool(Tool):
    """Tool for file system operations with safety constraints."""
    
    # Allowed base directories
    @property
    def allowed_dirs(self):
        """Get list of allowed directories including user-configured ones."""
        base_dirs = [ROOT_DIR, OUTPUT_DIR, KB_DIR]
        # Add user-accessible directories if configured
        if USER_ACCESSIBLE_DIRS:
            base_dirs.extend(USER_ACCESSIBLE_DIRS)
            logger.debug(f"Added {len(USER_ACCESSIBLE_DIRS)} user-accessible directories")
        return base_dirs
    
    @property
    def name(self) -> str:
        return "file_ops"
    
    @property
    def description(self) -> str:
        return "Read, write, or list files. Supports read_file, write_file, and list_directory operations."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["read_file", "write_file", "list_directory"],
                    "description": "File operation to perform"
                },
                "path": {
                    "type": "string",
                    "description": "File or directory path (relative to workspace or absolute within allowed directories)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write (required for write_file operation)"
                },
            },
            "required": ["operation", "path"]
        }
    
    def _validate_path(self, path: str) -> Path:
        """
        Validate path for safety.
        
        Args:
            path: User-provided path
        
        Returns:
            Resolved absolute path
        
        Raises:
            ValueError: If path is unsafe
        """
        # Convert to Path object
        if not os.path.isabs(path):
            # Relative path, resolve against workspace root
            full_path = (ROOT_DIR / path).resolve()
        else:
            full_path = Path(path).resolve()
        
        # Get allowed directories
        allowed_dirs = self.allowed_dirs
        
        # Check if path is within allowed directories
        allowed = False
        for allowed_dir in allowed_dirs:
            try:
                full_path.relative_to(allowed_dir.resolve())
                allowed = True
                break
            except ValueError:
                continue
        
        if not allowed:
            raise ValueError(
                f"Path '{path}' is outside allowed directories. "
                f"To allow access, set SENTINEL_USER_DIRS environment variable. "
                f"Currently allowed: Workspace, Output, KB"
            )
        
        # Check for parent directory escapes (only if path is relative)
        if not os.path.isabs(path) and ".." in path:
            raise ValueError("Parent directory references (..) not allowed in relative paths")
        
        return full_path
    
    def read_file(self, path: str) -> Dict[str, Any]:
        """Read file contents - delegates to document processor for supported types."""
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return {
                    "status": "error",
                    "error": f"File not found: {path}"
                }
            
            if not full_path.is_file():
                return {
                    "status": "error",
                    "error": f"Not a file: {path}"
                }
            
            suffix = full_path.suffix.lower()
            
            # Supported document types - redirect to document processor
            if suffix in ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', 
                         '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
                return {
                    "status": "info",
                    "output": f"Detected {suffix} file: {full_path.name}",
                    "metadata": {
                        "path": str(full_path),
                        "size_bytes": full_path.stat().st_size,
                        "type": suffix[1:],  # Remove the dot
                        "message": f"Use the 'process_document' tool to extract content from {suffix} files."
                    }
                }
            
            # Read file (assume text)
            try:
                content = full_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Binary file
                return {
                    "status": "info",
                    "output": f"Binary file detected: {full_path.name}",
                    "metadata": {
                        "path": str(full_path),
                        "size_bytes": full_path.stat().st_size,
                        "type": "binary",
                        "message": "This is a binary file and cannot be read as text."
                    }
                }
            
            return {
                "status": "success",
                "output": content,
                "metadata": {
                    "path": str(full_path),
                    "size_bytes": full_path.stat().st_size,
                }
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to file."""
        try:
            full_path = self._validate_path(path)
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            full_path.write_text(content, encoding='utf-8')
            
            return {
                "status": "success",
                "output": f"Written {len(content)} characters to {path}",
                "metadata": {
                    "path": str(full_path),
                    "size_bytes": len(content.encode('utf-8')),
                }
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def list_directory(self, path: str) -> Dict[str, Any]:
        """List directory contents."""
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return {
                    "status": "error",
                    "error": f"Directory not found: {path}"
                }
            
            if not full_path.is_dir():
                return {
                    "status": "error",
                    "error": f"Not a directory: {path}"
                }
            
            # List contents
            entries = []
            for entry in full_path.iterdir():
                entries.append({
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                    "size": entry.stat().st_size if entry.is_file() else None,
                })
            
            return {
                "status": "success",
                "output": f"Found {len(entries)} entries in {path}",
                "entries": entries,
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute file operation."""
        operation = kwargs.get("operation")
        path = kwargs.get("path")
        
        if operation == "read_file":
            return self.read_file(path)
        
        elif operation == "write_file":
            content = kwargs.get("content")
            if not content:
                return {
                    "status": "error",
                    "error": "content parameter required for write_file"
                }
            return self.write_file(path, content)
        
        elif operation == "list_directory":
            return self.list_directory(path)
        
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}"
            }
