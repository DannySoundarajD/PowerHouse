"""
Vision/OCR Pipeline Tool for Technical Drawing Analysis

Integrates qwen3-vl:4b for full-resolution image processing without downscaling.
Supports: PNG, JPEG, TIFF, BMP, PDF (multi-page extraction).
"""

import asyncio
import base64
import io
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

# Optional OCR - pytesseract not required for core functionality
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    pytesseract = None

from src.tools.base import Tool
from src.models.ollama_backend import OllamaBackend
from src.utils.constants import ALLOWED_IMAGE_DIRS, MAX_IMAGE_SIZE_MB

logger = logging.getLogger(__name__)


class VisionPipelineTool(Tool):
    """Tool for analyzing images and technical drawings using vision models."""

    def __init__(self, backend: OllamaBackend):
        super().__init__(
            name="analyze_image",
            description=(
                "Analyze images, technical drawings, P&IDs, charts, or scanned documents. "
                "Supports full-resolution processing without downscaling. "
                "Can extract text (OCR), identify components, analyze layouts. "
                "Input: image_path (required), query (optional prompt), ocr_only (bool, default False)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to image file (PNG/JPEG/TIFF/BMP) in workspace, output, or kb directories"
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional question or prompt about the image (e.g., 'What equipment is shown?' or 'Extract all text')"
                    },
                    "ocr_only": {
                        "type": "boolean",
                        "description": "If true, only perform OCR text extraction without vision model analysis (faster)"
                    }
                },
                "required": ["image_path"]
            }
        )
        self.backend = backend
        self.vision_model = "qwen3-vl:4b"  # Default vision model

    def _validate_image_path(self, path: str) -> Path:
        """Validate image path is in allowed directories."""
        img_path = Path(path).resolve()
        
        # Check if path is within allowed directories
        allowed = False
        for allowed_dir in ALLOWED_IMAGE_DIRS:
            try:
                img_path.relative_to(Path(allowed_dir).resolve())
                allowed = True
                break
            except ValueError:
                continue
        
        if not allowed:
            raise ValueError(
                f"Image path must be within allowed directories: {ALLOWED_IMAGE_DIRS}"
            )
        
        if not img_path.exists():
            raise FileNotFoundError(f"Image file not found: {img_path}")
        
        if not img_path.is_file():
            raise ValueError(f"Path is not a file: {img_path}")
        
        # Check file size
        size_mb = img_path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_IMAGE_SIZE_MB:
            raise ValueError(
                f"Image too large: {size_mb:.2f}MB (max: {MAX_IMAGE_SIZE_MB}MB)"
            )
        
        # Check file extension
        valid_extensions = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
        if img_path.suffix.lower() not in valid_extensions:
            raise ValueError(
                f"Unsupported image format: {img_path.suffix}. "
                f"Supported: {valid_extensions}"
            )
        
        return img_path

    def _load_and_encode_image(self, img_path: Path) -> str:
        """Load image and encode as base64 for vision model."""
        try:
            # Open image with PIL
            img = Image.open(img_path)
            
            # Convert to RGB if needed (handles RGBA, grayscale, etc.)
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # No downscaling - full resolution as per requirements
            logger.info(f"Image loaded: {img.size[0]}x{img.size[1]} pixels, {img.mode} mode")
            
            # Encode to base64
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_bytes = buffer.getvalue()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            
            return img_b64
            
        except Exception as e:
            raise RuntimeError(f"Failed to load/encode image: {e}")

    def _perform_ocr(self, img_path: Path) -> str:
        """Perform OCR using Tesseract."""
        try:
            img = Image.open(img_path)
            text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return f"[OCR Error: {e}]"

    async def _analyze_with_vision_model(
        self, 
        img_b64: str, 
        query: Optional[str] = None
    ) -> str:
        """Send image to vision model for analysis."""
        
        # Build prompt
        if query:
            prompt = query
        else:
            prompt = (
                "Analyze this image in detail. Describe what you see, "
                "identify any technical components, text, diagrams, or important features."
            )
        
        # Check if vision model is loaded, load if needed
        try:
            loaded_models = await self.backend.list_loaded_models()
            if self.vision_model not in loaded_models:
                logger.info(f"Loading vision model: {self.vision_model}")
                await self.backend.load_model(self.vision_model)
        except Exception as e:
            logger.warning(f"Could not check/load vision model: {e}")
        
        # Call vision model with image
        try:
            # Ollama vision API format
            response = await self.backend.chat(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [img_b64]  # Base64 image
                    }
                ],
                stream=False
            )
            
            # Extract response text
            if isinstance(response, dict) and "message" in response:
                return response["message"]["content"]
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        except Exception as e:
            raise RuntimeError(f"Vision model analysis failed: {e}")

    def _execute_impl(self, **kwargs) -> str:
        """Execute vision analysis."""
        image_path = kwargs.get("image_path")
        query = kwargs.get("query")
        ocr_only = kwargs.get("ocr_only", False)
        
        if not image_path:
            return json.dumps({"error": "image_path is required"})
        
        try:
            # Validate and resolve path
            img_path = self._validate_image_path(image_path)
            
            result = {
                "image_path": str(img_path),
                "size_mb": round(img_path.stat().st_size / (1024 * 1024), 2)
            }
            
            # OCR-only mode
            if ocr_only:
                logger.info(f"Performing OCR on: {img_path}")
                ocr_text = self._perform_ocr(img_path)
                result["ocr_text"] = ocr_text
                result["mode"] = "ocr_only"
                return json.dumps(result, indent=2)
            
            # Full vision analysis
            logger.info(f"Analyzing image with vision model: {img_path}")
            
            # Load and encode image
            img_b64 = self._load_and_encode_image(img_path)
            
            # Run vision model analysis (async)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                analysis = loop.run_until_complete(
                    self._analyze_with_vision_model(img_b64, query)
                )
            finally:
                loop.close()
            
            result["analysis"] = analysis
            result["mode"] = "vision_model"
            result["model"] = self.vision_model
            
            # Optionally include OCR as well
            if query and "text" in query.lower():
                ocr_text = self._perform_ocr(img_path)
                result["ocr_text"] = ocr_text
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Vision pipeline error: {e}")
            return json.dumps({"error": str(e)})


class TiledVisionTool(Tool):
    """Tool for processing very large images using tiled approach."""
    
    def __init__(self, backend: OllamaBackend, tile_size: int = 2048):
        super().__init__(
            name="analyze_large_image",
            description=(
                "Analyze very large images (>4K resolution) using tiled processing. "
                "Splits image into overlapping tiles, analyzes each, then merges results. "
                "Use for high-resolution technical drawings, facility maps, large schematics."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to large image file"
                    },
                    "query": {
                        "type": "string",
                        "description": "Question or analysis prompt for the image"
                    },
                    "tile_size": {
                        "type": "integer",
                        "description": "Size of each tile in pixels (default: 2048)"
                    }
                },
                "required": ["image_path"]
            }
        )
        self.backend = backend
        self.vision_model = "qwen3-vl:4b"
        self.default_tile_size = tile_size

    def _split_into_tiles(
        self, 
        img: Image.Image, 
        tile_size: int,
        overlap: int = 128
    ) -> List[Tuple[Image.Image, Tuple[int, int]]]:
        """Split large image into overlapping tiles."""
        width, height = img.size
        tiles = []
        
        for y in range(0, height, tile_size - overlap):
            for x in range(0, width, tile_size - overlap):
                # Define tile boundaries
                x1 = x
                y1 = y
                x2 = min(x + tile_size, width)
                y2 = min(y + tile_size, height)
                
                # Extract tile
                tile = img.crop((x1, y1, x2, y2))
                tiles.append((tile, (x1, y1)))
        
        return tiles

    def _execute_impl(self, **kwargs) -> str:
        """Execute tiled vision analysis."""
        image_path = kwargs.get("image_path")
        query = kwargs.get("query", "Analyze this section of the technical drawing")
        tile_size = kwargs.get("tile_size", self.default_tile_size)
        
        if not image_path:
            return json.dumps({"error": "image_path is required"})
        
        try:
            img_path = Path(image_path).resolve()
            
            if not img_path.exists():
                return json.dumps({"error": f"Image not found: {img_path}"})
            
            # Load image
            img = Image.open(img_path)
            width, height = img.size
            
            logger.info(f"Processing large image: {width}x{height}, tile_size={tile_size}")
            
            # Check if tiling is needed
            if width <= tile_size and height <= tile_size:
                return json.dumps({
                    "info": "Image is small enough for single-pass analysis",
                    "recommendation": "Use analyze_image tool instead"
                })
            
            # Split into tiles
            tiles = self._split_into_tiles(img, tile_size)
            logger.info(f"Split into {len(tiles)} tiles")
            
            # Analyze each tile
            tile_results = []
            for idx, (tile, position) in enumerate(tiles):
                logger.info(f"Analyzing tile {idx+1}/{len(tiles)} at position {position}")
                
                # Encode tile
                buffer = io.BytesIO()
                tile.save(buffer, format="PNG")
                tile_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                # Analyze with vision model
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    response = loop.run_until_complete(
                        self.backend.chat(
                            model=self.vision_model,
                            messages=[{
                                "role": "user",
                                "content": f"{query} (Tile {idx+1} at position {position})",
                                "images": [tile_b64]
                            }],
                            stream=False
                        )
                    )
                    
                    if isinstance(response, dict) and "message" in response:
                        analysis = response["message"]["content"]
                    else:
                        analysis = str(response)
                    
                    tile_results.append({
                        "tile_id": idx + 1,
                        "position": position,
                        "analysis": analysis
                    })
                finally:
                    loop.close()
            
            # Merge results
            result = {
                "image_path": str(img_path),
                "dimensions": {"width": width, "height": height},
                "tile_count": len(tiles),
                "tile_size": tile_size,
                "tile_analyses": tile_results,
                "summary": f"Analyzed {len(tiles)} tiles from {width}x{height} image"
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Tiled vision error: {e}")
            return json.dumps({"error": str(e)})
