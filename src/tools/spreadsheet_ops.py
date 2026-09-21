"""
Spreadsheet operations tool for Sentinel AI Workbench.
Read and write Excel and CSV files.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

from .base import Tool
from ..utils.constants import ROOT_DIR, OUTPUT_DIR
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SpreadsheetOpsTool(Tool):
    """Tool for reading and writing spreadsheet files."""
    
    ALLOWED_DIRS = [ROOT_DIR, OUTPUT_DIR]
    MAX_ROWS_DISPLAY = 100  # Limit rows in output to prevent context overflow
    
    def __init__(self):
        """Initialize spreadsheet tool."""
        self.pandas_available = PANDAS_AVAILABLE
        self.openpyxl_available = OPENPYXL_AVAILABLE
        
        if not PANDAS_AVAILABLE:
            logger.warning("pandas not available, spreadsheet functionality limited")
        if not OPENPYXL_AVAILABLE:
            logger.warning("openpyxl not available, Excel support limited")
    
    @property
    def name(self) -> str:
        return "spreadsheet_ops"
    
    @property
    def description(self) -> str:
        return "Read or write spreadsheet files (Excel .xlsx and CSV). Supports read_excel, write_excel, read_csv, write_csv operations."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["read_excel", "write_excel", "read_csv", "write_csv"],
                    "description": "Spreadsheet operation"
                },
                "path": {
                    "type": "string",
                    "description": "File path"
                },
                "data": {
                    "type": "array",
                    "description": "Data to write (array of arrays for rows). Required for write operations.",
                    "items": {"type": "array"}
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Sheet name for Excel operations (default: first sheet for read, 'Sheet1' for write)"
                },
                "headers": {
                    "type": "boolean",
                    "description": "Whether first row contains headers (default: true)",
                    "default": True
                },
            },
            "required": ["operation", "path"]
        }
    
    def _validate_path(self, path: str) -> Path:
        """Validate and resolve path."""
        if not Path(path).is_absolute():
            full_path = (ROOT_DIR / path).resolve()
        else:
            full_path = Path(path).resolve()
        
        # Check allowed directories
        allowed = any(
            str(full_path).startswith(str(d))
            for d in self.ALLOWED_DIRS
        )
        
        if not allowed:
            raise ValueError(f"Path outside allowed directories")
        
        return full_path
    
    def read_excel(
        self,
        path: str,
        sheet_name: Optional[str] = None,
        headers: bool = True
    ) -> Dict[str, Any]:
        """Read Excel file."""
        if not self.pandas_available:
            return {
                "status": "error",
                "error": "pandas not installed (pip install pandas openpyxl)"
            }
        
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return {"status": "error", "error": f"File not found: {path}"}
            
            # Read Excel
            header_row = 0 if headers else None
            df = pd.read_excel(
                full_path,
                sheet_name=sheet_name or 0,
                header=header_row
            )
            
            # Convert to list of lists
            if headers:
                data = [df.columns.tolist()] + df.values.tolist()
            else:
                data = df.values.tolist()
            
            # Limit rows for display
            if len(data) > self.MAX_ROWS_DISPLAY:
                data = data[:self.MAX_ROWS_DISPLAY]
                truncated = True
            else:
                truncated = False
            
            return {
                "status": "success",
                "output": f"Read {len(df)} rows from {path}",
                "data": data,
                "metadata": {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "truncated": truncated,
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to read Excel: {e}")
            return {"status": "error", "error": str(e)}
    
    def write_excel(
        self,
        path: str,
        data: List[List],
        sheet_name: str = "Sheet1",
        headers: bool = True
    ) -> Dict[str, Any]:
        """Write Excel file."""
        if not self.pandas_available or not self.openpyxl_available:
            return {
                "status": "error",
                "error": "pandas and openpyxl required (pip install pandas openpyxl)"
            }
        
        try:
            full_path = self._validate_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to DataFrame
            if headers and len(data) > 0:
                df = pd.DataFrame(data[1:], columns=data[0])
            else:
                df = pd.DataFrame(data)
            
            # Write to Excel
            df.to_excel(full_path, sheet_name=sheet_name, index=False)
            
            return {
                "status": "success",
                "output": f"Written {len(df)} rows to {path}",
                "metadata": {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "path": str(full_path),
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to write Excel: {e}")
            return {"status": "error", "error": str(e)}
    
    def read_csv(
        self,
        path: str,
        headers: bool = True
    ) -> Dict[str, Any]:
        """Read CSV file."""
        if not self.pandas_available:
            return {
                "status": "error",
                "error": "pandas not installed (pip install pandas)"
            }
        
        try:
            full_path = self._validate_path(path)
            
            if not full_path.exists():
                return {"status": "error", "error": f"File not found: {path}"}
            
            # Read CSV
            header_row = 0 if headers else None
            df = pd.read_csv(full_path, header=header_row)
            
            # Convert to list of lists
            if headers:
                data = [df.columns.tolist()] + df.values.tolist()
            else:
                data = df.values.tolist()
            
            # Limit rows
            if len(data) > self.MAX_ROWS_DISPLAY:
                data = data[:self.MAX_ROWS_DISPLAY]
                truncated = True
            else:
                truncated = False
            
            return {
                "status": "success",
                "output": f"Read {len(df)} rows from {path}",
                "data": data,
                "metadata": {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "truncated": truncated,
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to read CSV: {e}")
            return {"status": "error", "error": str(e)}
    
    def write_csv(
        self,
        path: str,
        data: List[List],
        headers: bool = True
    ) -> Dict[str, Any]:
        """Write CSV file."""
        if not self.pandas_available:
            return {
                "status": "error",
                "error": "pandas not installed (pip install pandas)"
            }
        
        try:
            full_path = self._validate_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to DataFrame
            if headers and len(data) > 0:
                df = pd.DataFrame(data[1:], columns=data[0])
            else:
                df = pd.DataFrame(data)
            
            # Write to CSV
            df.to_csv(full_path, index=False)
            
            return {
                "status": "success",
                "output": f"Written {len(df)} rows to {path}",
                "metadata": {
                    "rows": len(df),
                    "columns": len(df.columns),
                    "path": str(full_path),
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to write CSV: {e}")
            return {"status": "error", "error": str(e)}
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute spreadsheet operation."""
        operation = kwargs.get("operation")
        path = kwargs.get("path")
        data = kwargs.get("data")
        sheet_name = kwargs.get("sheet_name", "Sheet1")
        headers = kwargs.get("headers", True)
        
        if operation == "read_excel":
            return self.read_excel(path, sheet_name, headers)
        
        elif operation == "write_excel":
            if not data:
                return {"status": "error", "error": "data required for write_excel"}
            return self.write_excel(path, data, sheet_name, headers)
        
        elif operation == "read_csv":
            return self.read_csv(path, headers)
        
        elif operation == "write_csv":
            if not data:
                return {"status": "error", "error": "data required for write_csv"}
            return self.write_csv(path, data, headers)
        
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}
