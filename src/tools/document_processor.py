"""
Comprehensive Document Processor for all file types.
Handles PDF, Word, Excel, PowerPoint, and images.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Document processing imports
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False

try:
    import openpyxl
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    from pptx import Presentation
    PYTHON_PPTX_AVAILABLE = True
except ImportError:
    PYTHON_PPTX_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from .base import Tool
from ..utils.constants import ROOT_DIR, OUTPUT_DIR, KB_DIR, USER_ACCESSIBLE_DIRS
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DocumentProcessorTool(Tool):
    """Tool for processing various document types (PDF, Word, Excel, PowerPoint, Images)."""
    
    @property
    def name(self) -> str:
        return "process_document"
    
    @property
    def description(self) -> str:
        return (
            "Process and extract content from various document types including PDF, "
            "Word (.docx), Excel (.xlsx), PowerPoint (.pptx), and images (.png, .jpg, .jpeg). "
            "Returns extracted text, metadata, and structure information."
        )
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the document file"
                },
                "max_pages": {
                    "type": "integer",
                    "description": "For PDFs/presentations: max pages to process (optional)"
                },
                "extract_images": {
                    "type": "boolean",
                    "description": "For documents: whether to extract embedded images (default: false)"
                }
            },
            "required": ["file_path"]
        }
    
    def _get_allowed_dirs(self) -> List[Path]:
        """Get list of allowed directories."""
        base_dirs = [ROOT_DIR, OUTPUT_DIR, KB_DIR]
        if USER_ACCESSIBLE_DIRS:
            base_dirs.extend(USER_ACCESSIBLE_DIRS)
        return base_dirs
    
    def _validate_path(self, path: str) -> Path:
        """Validate file path is in allowed directories."""
        file_path = Path(path).resolve()
        
        # Check if path is within allowed directories
        allowed = False
        for allowed_dir in self._get_allowed_dirs():
            try:
                file_path.relative_to(allowed_dir.resolve())
                allowed = True
                break
            except ValueError:
                continue
        
        if not allowed:
            raise ValueError(
                f"File path must be within allowed directories. "
                f"Set SENTINEL_USER_DIRS environment variable to add more directories."
            )
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        return file_path
    
    def _process_pdf(self, file_path: Path, max_pages: Optional[int] = None) -> Dict[str, Any]:
        """Extract text from PDF using PyPDF2."""
        if not PYPDF2_AVAILABLE:
            return {
                "error": "PyPDF2 not installed. Run: pip install PyPDF2",
                "type": "pdf"
            }
        
        try:
            result = {
                "type": "pdf",
                "file_name": file_path.name,
                "file_path": str(file_path),
                "size_bytes": file_path.stat().st_size
            }
            
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                total_pages = len(pdf_reader.pages)
                pages_to_process = min(max_pages, total_pages) if max_pages else total_pages
                
                result["total_pages"] = total_pages
                result["processed_pages"] = pages_to_process
                
                # Extract metadata
                if pdf_reader.metadata:
                    result["metadata"] = {
                        "title": pdf_reader.metadata.get('/Title', ''),
                        "author": pdf_reader.metadata.get('/Author', ''),
                        "subject": pdf_reader.metadata.get('/Subject', ''),
                        "creator": pdf_reader.metadata.get('/Creator', '')
                    }
                
                # Extract text from each page
                pages = []
                full_text = []
                
                for page_num in range(pages_to_process):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    
                    pages.append({
                        "page_number": page_num + 1,
                        "text": text,
                        "word_count": len(text.split())
                    })
                    
                    full_text.append(text)
                
                result["pages"] = pages
                result["full_text"] = "\n\n".join(full_text)
                result["total_words"] = sum(p["word_count"] for p in pages)
                result["status"] = "success"
                
                return result
                
        except Exception as e:
            logger.error(f"PDF processing error: {e}", exc_info=True)
            return {
                "error": str(e),
                "type": "pdf",
                "file_name": file_path.name
            }
    
    def _process_docx(self, file_path: Path) -> Dict[str, Any]:
        """Extract text from Word document."""
        if not PYTHON_DOCX_AVAILABLE:
            return {
                "error": "python-docx not installed. Run: pip install python-docx",
                "type": "docx"
            }
        
        try:
            result = {
                "type": "docx",
                "file_name": file_path.name,
                "file_path": str(file_path),
                "size_bytes": file_path.stat().st_size
            }
            
            doc = DocxDocument(file_path)
            
            # Extract core properties
            if doc.core_properties:
                result["metadata"] = {
                    "title": doc.core_properties.title or "",
                    "author": doc.core_properties.author or "",
                    "subject": doc.core_properties.subject or "",
                    "keywords": doc.core_properties.keywords or "",
                    "created": str(doc.core_properties.created) if doc.core_properties.created else "",
                    "modified": str(doc.core_properties.modified) if doc.core_properties.modified else ""
                }
            
            # Extract paragraphs
            paragraphs = []
            for i, para in enumerate(doc.paragraphs):
                if para.text.strip():
                    paragraphs.append({
                        "paragraph_number": i + 1,
                        "text": para.text,
                        "style": para.style.name if para.style else "Normal"
                    })
            
            result["paragraphs"] = paragraphs
            result["total_paragraphs"] = len(paragraphs)
            result["full_text"] = "\n\n".join(p["text"] for p in paragraphs)
            result["total_words"] = len(result["full_text"].split())
            
            # Extract tables if any
            if doc.tables:
                tables = []
                for i, table in enumerate(doc.tables):
                    table_data = []
                    for row in table.rows:
                        row_data = [cell.text for cell in row.cells]
                        table_data.append(row_data)
                    
                    tables.append({
                        "table_number": i + 1,
                        "rows": len(table.rows),
                        "columns": len(table.columns),
                        "data": table_data
                    })
                
                result["tables"] = tables
                result["total_tables"] = len(tables)
            
            result["status"] = "success"
            return result
            
        except Exception as e:
            logger.error(f"DOCX processing error: {e}", exc_info=True)
            return {
                "error": str(e),
                "type": "docx",
                "file_name": file_path.name
            }
    
    def _process_xlsx(self, file_path: Path) -> Dict[str, Any]:
        """Extract data from Excel spreadsheet."""
        if not OPENPYXL_AVAILABLE:
            return {
                "error": "openpyxl not installed. Run: pip install openpyxl",
                "type": "xlsx"
            }
        
        try:
            result = {
                "type": "xlsx",
                "file_name": file_path.name,
                "file_path": str(file_path),
                "size_bytes": file_path.stat().st_size
            }
            
            workbook = load_workbook(file_path, data_only=True)
            
            # Extract metadata
            result["total_sheets"] = len(workbook.sheetnames)
            result["sheet_names"] = workbook.sheetnames
            
            # Process each sheet
            sheets = []
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                
                # Get data dimensions
                max_row = sheet.max_row
                max_col = sheet.max_column
                
                # Extract data (limit to reasonable size)
                data = []
                for row in sheet.iter_rows(min_row=1, max_row=min(max_row, 100), values_only=True):
                    # Convert None to empty string, handle various types
                    row_data = [str(cell) if cell is not None else "" for cell in row]
                    data.append(row_data)
                
                sheet_info = {
                    "name": sheet_name,
                    "rows": max_row,
                    "columns": max_col,
                    "data": data,
                    "data_preview_rows": len(data)
                }
                
                sheets.append(sheet_info)
            
            result["sheets"] = sheets
            result["status"] = "success"
            
            return result
            
        except Exception as e:
            logger.error(f"XLSX processing error: {e}", exc_info=True)
            return {
                "error": str(e),
                "type": "xlsx",
                "file_name": file_path.name
            }
    
    def _process_pptx(self, file_path: Path, max_slides: Optional[int] = None) -> Dict[str, Any]:
        """Extract text from PowerPoint presentation."""
        if not PYTHON_PPTX_AVAILABLE:
            return {
                "error": "python-pptx not installed. Run: pip install python-pptx",
                "type": "pptx"
            }
        
        try:
            result = {
                "type": "pptx",
                "file_name": file_path.name,
                "file_path": str(file_path),
                "size_bytes": file_path.stat().st_size
            }
            
            prs = Presentation(file_path)
            
            total_slides = len(prs.slides)
            slides_to_process = min(max_slides, total_slides) if max_slides else total_slides
            
            result["total_slides"] = total_slides
            result["processed_slides"] = slides_to_process
            
            # Extract core properties if available
            if prs.core_properties:
                result["metadata"] = {
                    "title": prs.core_properties.title or "",
                    "author": prs.core_properties.author or "",
                    "subject": prs.core_properties.subject or "",
                    "created": str(prs.core_properties.created) if prs.core_properties.created else "",
                    "modified": str(prs.core_properties.modified) if prs.core_properties.modified else ""
                }
            
            # Process each slide
            slides = []
            full_text = []
            
            for i, slide in enumerate(prs.slides[:slides_to_process]):
                slide_text = []
                
                # Extract text from all shapes
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text = shape.text.strip()
                        if text:
                            slide_text.append(text)
                
                slide_content = "\n".join(slide_text)
                slides.append({
                    "slide_number": i + 1,
                    "text": slide_content,
                    "word_count": len(slide_content.split())
                })
                
                full_text.append(slide_content)
            
            result["slides"] = slides
            result["full_text"] = "\n\n---\n\n".join(full_text)
            result["total_words"] = sum(s["word_count"] for s in slides)
            result["status"] = "success"
            
            return result
            
        except Exception as e:
            logger.error(f"PPTX processing error: {e}", exc_info=True)
            return {
                "error": str(e),
                "type": "pptx",
                "file_name": file_path.name
            }
    
    def _process_image(self, file_path: Path) -> Dict[str, Any]:
        """Get image metadata and basic info."""
        if not PIL_AVAILABLE:
            return {
                "error": "Pillow not installed. Run: pip install Pillow",
                "type": "image"
            }
        
        try:
            result = {
                "type": "image",
                "file_name": file_path.name,
                "file_path": str(file_path),
                "size_bytes": file_path.stat().st_size
            }
            
            with Image.open(file_path) as img:
                result["format"] = img.format
                result["mode"] = img.mode
                result["width"] = img.width
                result["height"] = img.height
                result["size"] = f"{img.width}x{img.height}"
                
                # Get EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    result["exif"] = {k: str(v) for k, v in exif.items() if v}
                
                result["message"] = (
                    f"Image file: {img.format}, {img.width}x{img.height}, {img.mode} mode. "
                    "Use vision tools to analyze image content."
                )
            
            result["status"] = "success"
            return result
            
        except Exception as e:
            logger.error(f"Image processing error: {e}", exc_info=True)
            return {
                "error": str(e),
                "type": "image",
                "file_name": file_path.name
            }
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute document processing based on file type."""
        file_path_str = kwargs.get("file_path")
        max_pages = kwargs.get("max_pages")
        extract_images = kwargs.get("extract_images", False)
        
        if not file_path_str:
            return {
                "status": "error",
                "error": "file_path parameter is required"
            }
        
        try:
            # Validate and get file path
            file_path = self._validate_path(file_path_str)
            
            # Determine file type and process accordingly
            suffix = file_path.suffix.lower()
            
            if suffix == '.pdf':
                result = self._process_pdf(file_path, max_pages)
            elif suffix in ['.docx', '.doc']:
                result = self._process_docx(file_path)
            elif suffix in ['.xlsx', '.xls']:
                result = self._process_xlsx(file_path)
            elif suffix in ['.pptx', '.ppt']:
                result = self._process_pptx(file_path, max_pages)
            elif suffix in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']:
                result = self._process_image(file_path)
            else:
                result = {
                    "status": "error",
                    "error": f"Unsupported file type: {suffix}",
                    "supported_types": [".pdf", ".docx", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg"]
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Document processing error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
