"""
PDF Multi-Page Processor for Scanned Documents

Extracts pages as images, performs OCR and vision analysis on each page.
Handles technical manuals, SOPs, scanned forms.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

# Optional imports - not required for core functionality
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    convert_from_path = None

from PIL import Image

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    pytesseract = None

from src.tools.base import Tool
from src.tools.vision_pipeline import VisionPipelineTool
from src.models.ollama_backend import OllamaBackend
from src.utils.constants import ALLOWED_IMAGE_DIRS

logger = logging.getLogger(__name__)


class PDFProcessorTool(Tool):
    """Tool for processing multi-page PDF documents."""
    
    def __init__(self, backend: OllamaBackend):
        super().__init__(
            name="process_pdf",
            description=(
                "Process multi-page PDF documents. Extracts each page as image, "
                "performs OCR and optional vision analysis. Use for scanned manuals, "
                "SOPs, technical documentation, forms. "
                "Input: pdf_path, mode (ocr/vision/both), max_pages (optional limit)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "Path to PDF file in workspace, output, or kb directories"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["ocr", "vision", "both"],
                        "description": "Processing mode: 'ocr' (text only), 'vision' (vision model), 'both' (default)"
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "Maximum number of pages to process (default: all pages)"
                    },
                    "dpi": {
                        "type": "integer",
                        "description": "DPI for PDF to image conversion (default: 200, higher = better quality)"
                    }
                },
                "required": ["pdf_path"]
            }
        )
        self.backend = backend
        self.vision_tool = VisionPipelineTool(backend)

    def _validate_pdf_path(self, path: str) -> Path:
        """Validate PDF path is in allowed directories."""
        pdf_path = Path(path).resolve()
        
        # Check if path is within allowed directories
        allowed = False
        for allowed_dir in ALLOWED_IMAGE_DIRS:
            try:
                pdf_path.relative_to(Path(allowed_dir).resolve())
                allowed = True
                break
            except ValueError:
                continue
        
        if not allowed:
            raise ValueError(
                f"PDF path must be within allowed directories: {ALLOWED_IMAGE_DIRS}"
            )
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if not pdf_path.is_file():
            raise ValueError(f"Path is not a file: {pdf_path}")
        
        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(f"Not a PDF file: {pdf_path}")
        
        return pdf_path

    def _convert_pdf_to_images(
        self, 
        pdf_path: Path, 
        dpi: int = 200,
        max_pages: Optional[int] = None
    ) -> List[Image.Image]:
        """Convert PDF pages to PIL Images."""
        try:
            if max_pages:
                images = convert_from_path(
                    pdf_path, 
                    dpi=dpi,
                    last_page=max_pages
                )
            else:
                images = convert_from_path(pdf_path, dpi=dpi)
            
            return images
        except Exception as e:
            raise RuntimeError(f"Failed to convert PDF to images: {e}")

    def _process_page_ocr(self, page_img: Image.Image, page_num: int) -> Dict[str, Any]:
        """Process single page with OCR."""
        try:
            text = pytesseract.image_to_string(page_img)
            return {
                "page": page_num,
                "text": text.strip(),
                "word_count": len(text.split()),
                "mode": "ocr"
            }
        except Exception as e:
            return {
                "page": page_num,
                "error": str(e),
                "mode": "ocr"
            }

    def _process_page_vision(
        self, 
        page_img: Image.Image, 
        page_num: int,
        temp_path: Path
    ) -> Dict[str, Any]:
        """Process single page with vision model."""
        try:
            # Save temporary image
            page_path = temp_path / f"page_{page_num}.png"
            page_img.save(page_path, "PNG")
            
            # Use vision tool
            result_json = self.vision_tool._execute_impl(
                image_path=str(page_path),
                query=f"Analyze page {page_num} of this document. Describe content, extract key information."
            )
            
            result = json.loads(result_json)
            result["page"] = page_num
            
            # Clean up temp file
            page_path.unlink(missing_ok=True)
            
            return result
            
        except Exception as e:
            return {
                "page": page_num,
                "error": str(e),
                "mode": "vision"
            }

    def _execute_impl(self, **kwargs) -> str:
        """Execute PDF processing."""
        pdf_path_str = kwargs.get("pdf_path")
        mode = kwargs.get("mode", "both")
        max_pages = kwargs.get("max_pages")
        dpi = kwargs.get("dpi", 200)
        
        if not pdf_path_str:
            return json.dumps({"error": "pdf_path is required"})
        
        try:
            # Validate path
            pdf_path = self._validate_pdf_path(pdf_path_str)
            
            logger.info(f"Processing PDF: {pdf_path}, mode={mode}, dpi={dpi}")
            
            # Convert PDF to images
            page_images = self._convert_pdf_to_images(pdf_path, dpi, max_pages)
            total_pages = len(page_images)
            
            logger.info(f"PDF has {total_pages} pages")
            
            # Create temp directory for page images
            temp_dir = pdf_path.parent / ".pdf_temp"
            temp_dir.mkdir(exist_ok=True)
            
            # Process each page
            results = []
            for idx, page_img in enumerate(page_images, start=1):
                logger.info(f"Processing page {idx}/{total_pages}")
                
                page_result = {"page": idx}
                
                # OCR mode
                if mode in ["ocr", "both"]:
                    ocr_result = self._process_page_ocr(page_img, idx)
                    page_result["ocr"] = ocr_result
                
                # Vision mode
                if mode in ["vision", "both"]:
                    vision_result = self._process_page_vision(page_img, idx, temp_dir)
                    page_result["vision"] = vision_result
                
                results.append(page_result)
            
            # Clean up temp directory
            try:
                for f in temp_dir.glob("*.png"):
                    f.unlink()
                temp_dir.rmdir()
            except Exception as e:
                logger.warning(f"Failed to clean temp directory: {e}")
            
            # Build final result
            output = {
                "pdf_path": str(pdf_path),
                "total_pages": total_pages,
                "processed_pages": len(results),
                "mode": mode,
                "dpi": dpi,
                "pages": results
            }
            
            # Add summary statistics
            if mode in ["ocr", "both"]:
                total_words = sum(
                    p.get("ocr", {}).get("word_count", 0) 
                    for p in results
                )
                output["total_words_extracted"] = total_words
            
            return json.dumps(output, indent=2)
            
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            return json.dumps({"error": str(e)})


class DocumentSplitterTool(Tool):
    """Tool for splitting PDF into individual pages."""
    
    def __init__(self):
        super().__init__(
            name="split_pdf",
            description=(
                "Split multi-page PDF into individual page images (PNG). "
                "Saves each page as separate file for individual processing. "
                "Use before analyze_image if you need to process specific pages."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "Path to PDF file"
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory to save page images (default: same as PDF)"
                    },
                    "page_range": {
                        "type": "string",
                        "description": "Page range to extract, e.g. '1-5' or '2,4,6' (default: all)"
                    },
                    "dpi": {
                        "type": "integer",
                        "description": "DPI for output images (default: 200)"
                    }
                },
                "required": ["pdf_path"]
            }
        )

    def _parse_page_range(self, range_str: str, max_pages: int) -> List[int]:
        """Parse page range string into list of page numbers."""
        if not range_str:
            return list(range(1, max_pages + 1))
        
        pages = set()
        
        for part in range_str.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-")
                start = int(start.strip())
                end = int(end.strip())
                pages.update(range(start, end + 1))
            else:
                pages.add(int(part))
        
        # Filter valid pages
        return sorted([p for p in pages if 1 <= p <= max_pages])

    def _execute_impl(self, **kwargs) -> str:
        """Execute PDF splitting."""
        pdf_path_str = kwargs.get("pdf_path")
        output_dir_str = kwargs.get("output_dir")
        page_range = kwargs.get("page_range")
        dpi = kwargs.get("dpi", 200)
        
        if not pdf_path_str:
            return json.dumps({"error": "pdf_path is required"})
        
        try:
            pdf_path = Path(pdf_path_str).resolve()
            
            if not pdf_path.exists():
                return json.dumps({"error": f"PDF not found: {pdf_path}"})
            
            # Determine output directory
            if output_dir_str:
                output_dir = Path(output_dir_str).resolve()
            else:
                output_dir = pdf_path.parent / f"{pdf_path.stem}_pages"
            
            output_dir.mkdir(exist_ok=True)
            
            # Convert PDF to images
            logger.info(f"Converting PDF: {pdf_path}")
            images = convert_from_path(pdf_path, dpi=dpi)
            
            # Parse page range
            pages_to_extract = self._parse_page_range(page_range, len(images))
            
            logger.info(f"Extracting pages: {pages_to_extract}")
            
            # Save pages
            saved_files = []
            for page_num in pages_to_extract:
                img = images[page_num - 1]  # 0-indexed
                output_path = output_dir / f"page_{page_num:03d}.png"
                img.save(output_path, "PNG")
                saved_files.append(str(output_path))
            
            result = {
                "pdf_path": str(pdf_path),
                "output_dir": str(output_dir),
                "total_pages": len(images),
                "extracted_pages": len(saved_files),
                "page_files": saved_files
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"PDF splitting error: {e}")
            return json.dumps({"error": str(e)})
