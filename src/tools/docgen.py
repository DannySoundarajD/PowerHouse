"""
Document generation tool for Sentinel AI Workbench.
Generate Word, PowerPoint, and Excel documents.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from docx import Document
    from docx.shared import Inches, Pt
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from pptx import Presentation
    from pptx.util import Inches as PptxInches, Pt as PptxPt
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

from .base import Tool
from ..utils.constants import OUTPUT_DIR
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DocGenTool(Tool):
    """Tool for generating documents (Word, PowerPoint, Excel)."""
    
    def __init__(self):
        """Initialize document generation tool."""
        self.docx_available = DOCX_AVAILABLE
        self.pptx_available = PPTX_AVAILABLE
        
        if not DOCX_AVAILABLE:
            logger.warning("python-docx not available (pip install python-docx)")
        if not PPTX_AVAILABLE:
            logger.warning("python-pptx not available (pip install python-pptx)")
    
    @property
    def name(self) -> str:
        return "generate_document"
    
    @property
    def description(self) -> str:
        return "Generate Word (.docx) or PowerPoint (.pptx) documents. Supports create_word and create_powerpoint operations."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["create_word", "create_powerpoint"],
                    "description": "Document type to create"
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename (will be saved in output directory)"
                },
                "title": {
                    "type": "string",
                    "description": "Document title"
                },
                "content": {
                    "type": "string",
                    "description": "Document content (for Word documents)"
                },
                "slides": {
                    "type": "array",
                    "description": "Slide content for PowerPoint (array of {title, content} objects)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content": {"type": "string"}
                        }
                    }
                },
            },
            "required": ["operation", "filename"]
        }
    
    def _get_output_path(self, filename: str) -> Path:
        """Get full output path."""
        output_path = OUTPUT_DIR / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path
    
    def create_word(
        self,
        filename: str,
        title: Optional[str] = None,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create Word document."""
        if not self.docx_available:
            return {
                "status": "error",
                "error": "python-docx not installed (pip install python-docx)"
            }
        
        try:
            output_path = self._get_output_path(filename)
            
            # Create document
            doc = Document()
            
            # Add title
            if title:
                doc.add_heading(title, level=0)
            
            # Add content
            if content:
                # Split by newlines and add paragraphs
                paragraphs = content.split('\n\n')
                for para in paragraphs:
                    if para.strip():
                        # Check if it's a heading (starts with #)
                        if para.strip().startswith('#'):
                            # Count # for heading level
                            level = 0
                            while level < len(para) and para[level] == '#':
                                level += 1
                            heading_text = para[level:].strip()
                            doc.add_heading(heading_text, level=min(level, 3))
                        else:
                            doc.add_paragraph(para.strip())
            
            # Save
            doc.save(str(output_path))
            
            return {
                "status": "success",
                "output": f"Created Word document: {filename}",
                "metadata": {
                    "path": str(output_path),
                    "size_bytes": output_path.stat().st_size,
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to create Word document: {e}")
            return {"status": "error", "error": str(e)}
    
    def create_powerpoint(
        self,
        filename: str,
        title: Optional[str] = None,
        slides: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Create PowerPoint presentation."""
        if not self.pptx_available:
            return {
                "status": "error",
                "error": "python-pptx not installed (pip install python-pptx)"
            }
        
        try:
            output_path = self._get_output_path(filename)
            
            # Create presentation
            prs = Presentation()
            
            # Add title slide
            if title:
                title_slide_layout = prs.slide_layouts[0]
                slide = prs.slides.add_slide(title_slide_layout)
                slide.shapes.title.text = title
            
            # Add content slides
            if slides:
                bullet_slide_layout = prs.slide_layouts[1]  # Title and Content
                
                for slide_data in slides:
                    slide = prs.slides.add_slide(bullet_slide_layout)
                    
                    # Set title
                    if "title" in slide_data:
                        slide.shapes.title.text = slide_data["title"]
                    
                    # Set content
                    if "content" in slide_data:
                        content = slide_data["content"]
                        text_frame = slide.placeholders[1].text_frame
                        
                        # Split content by newlines for bullet points
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if line.strip():
                                if i == 0:
                                    text_frame.text = line.strip()
                                else:
                                    p = text_frame.add_paragraph()
                                    p.text = line.strip()
                                    p.level = 0
            
            # Save
            prs.save(str(output_path))
            
            return {
                "status": "success",
                "output": f"Created PowerPoint presentation: {filename}",
                "metadata": {
                    "path": str(output_path),
                    "slides": len(prs.slides),
                    "size_bytes": output_path.stat().st_size,
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to create PowerPoint: {e}")
            return {"status": "error", "error": str(e)}
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute document generation."""
        operation = kwargs.get("operation")
        filename = kwargs.get("filename")
        title = kwargs.get("title")
        content = kwargs.get("content")
        slides = kwargs.get("slides")
        
        if operation == "create_word":
            return self.create_word(filename, title, content)
        
        elif operation == "create_powerpoint":
            return self.create_powerpoint(filename, title, slides)
        
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}
