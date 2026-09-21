"""
Tests for vision and PDF processing tools.
"""

import pytest
from pathlib import Path
from PIL import Image
import io

from src.tools.vision_pipeline import VisionPipelineTool, TiledVisionTool
from src.tools.pdf_processor import PDFProcessorTool, DocumentSplitterTool
from src.models.ollama_backend import OllamaBackend


@pytest.fixture
def backend():
    """Mock Ollama backend for testing."""
    class MockBackend:
        async def chat(self, model, messages, stream=False):
            return {
                "message": {
                    "content": "Mock vision analysis: This is a test image."
                }
            }
        
        async def list_loaded_models(self):
            return ["qwen3-vl:4b"]
        
        async def load_model(self, model):
            pass
    
    return MockBackend()


@pytest.fixture
def test_image(tmp_path):
    """Create a test image."""
    img_path = tmp_path / "test.png"
    
    # Create a simple test image
    img = Image.new('RGB', (800, 600), color='red')
    img.save(img_path)
    
    return img_path


@pytest.fixture
def large_image(tmp_path):
    """Create a large test image."""
    img_path = tmp_path / "large.png"
    
    # Create a 5000x5000 image
    img = Image.new('RGB', (5000, 5000), color='blue')
    img.save(img_path)
    
    return img_path


class TestVisionPipelineTool:
    """Test VisionPipelineTool."""
    
    def test_tool_initialization(self, backend):
        """Test tool can be initialized."""
        tool = VisionPipelineTool(backend)
        
        assert tool.name == "analyze_image"
        assert tool.description
        assert "image_path" in tool.parameters["properties"]
    
    def test_tool_schema(self, backend):
        """Test OpenAI tool schema generation."""
        tool = VisionPipelineTool(backend)
        schema = tool.to_openai_tool()
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "analyze_image"
        assert "parameters" in schema["function"]
    
    def test_path_validation(self, backend, test_image, tmp_path):
        """Test image path validation."""
        tool = VisionPipelineTool(backend)
        
        # Valid path (in tmp_path which simulates workspace)
        # Note: In real usage, path must be in ALLOWED_IMAGE_DIRS
        # For testing, we'll test the validation logic
        
        # Test non-existent file
        with pytest.raises(FileNotFoundError):
            tool._validate_image_path(str(tmp_path / "nonexistent.png"))
        
        # Test invalid extension
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("test")
        with pytest.raises(ValueError, match="Unsupported image format"):
            tool._validate_image_path(str(txt_file))
    
    def test_image_encoding(self, backend, test_image):
        """Test image loading and base64 encoding."""
        tool = VisionPipelineTool(backend)
        
        b64_str = tool._load_and_encode_image(test_image)
        
        assert isinstance(b64_str, str)
        assert len(b64_str) > 0
        # Base64 strings should be ASCII
        assert b64_str.isascii()


class TestTiledVisionTool:
    """Test TiledVisionTool for large images."""
    
    def test_tool_initialization(self, backend):
        """Test tool initialization."""
        tool = TiledVisionTool(backend, tile_size=2048)
        
        assert tool.name == "analyze_large_image"
        assert tool.default_tile_size == 2048
    
    def test_image_splitting(self, backend, large_image):
        """Test image is split into tiles correctly."""
        tool = TiledVisionTool(backend, tile_size=2048)
        
        img = Image.open(large_image)
        tiles = tool._split_into_tiles(img, tile_size=2048, overlap=128)
        
        # 5000x5000 image with 2048 tiles should produce ~6-9 tiles
        assert len(tiles) > 1
        
        # Each tile should be a PIL Image
        for tile, position in tiles:
            assert isinstance(tile, Image.Image)
            assert isinstance(position, tuple)
            assert len(position) == 2


class TestPDFProcessorTool:
    """Test PDFProcessorTool."""
    
    def test_tool_initialization(self, backend):
        """Test tool initialization."""
        tool = PDFProcessorTool(backend)
        
        assert tool.name == "process_pdf"
        assert "pdf_path" in tool.parameters["properties"]
        assert "mode" in tool.parameters["properties"]


class TestDocumentSplitterTool:
    """Test DocumentSplitterTool."""
    
    def test_tool_initialization(self):
        """Test tool initialization."""
        tool = DocumentSplitterTool()
        
        assert tool.name == "split_pdf"
        assert "pdf_path" in tool.parameters["properties"]
    
    def test_page_range_parsing(self):
        """Test page range string parsing."""
        tool = DocumentSplitterTool()
        
        # Test range
        pages = tool._parse_page_range("1-5", max_pages=10)
        assert pages == [1, 2, 3, 4, 5]
        
        # Test individual pages
        pages = tool._parse_page_range("2,4,6", max_pages=10)
        assert pages == [2, 4, 6]
        
        # Test mixed
        pages = tool._parse_page_range("1-3,5,7-9", max_pages=10)
        assert pages == [1, 2, 3, 5, 7, 8, 9]
        
        # Test all pages
        pages = tool._parse_page_range("", max_pages=5)
        assert pages == [1, 2, 3, 4, 5]
        
        # Test clamping
        pages = tool._parse_page_range("1-20", max_pages=10)
        assert max(pages) <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
