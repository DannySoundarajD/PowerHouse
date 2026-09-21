"""Tool implementations for Sentinel AI Workbench."""

from .base import Tool, ToolExecutionError, ToolValidationError
from .registry import ToolRegistry, get_tool_registry
from .file_ops import FileOpsTool
from .sandbox_exec import SandboxExecTool
from .spreadsheet_ops import SpreadsheetOpsTool
from .docgen import DocGenTool
from .vision_pipeline import VisionPipelineTool, TiledVisionTool
from .pdf_processor import PDFProcessorTool, DocumentSplitterTool
from .document_processor import DocumentProcessorTool
from .local_rag import LocalRAGTool, SemanticSearchTool, KBStatsTool, KBDeleteTool
from .geospatial import (
    GeospatialCoordinateTool,
    FacilityMapTool,
    PIDOverlayTool,
    SafetyZoneTool,
)
from .gods_eye_view import GodsEyeViewTool


def register_default_tools():
    """Register all default tools with error handling."""
    from ..models.ollama_backend import get_ollama_backend
    from ..utils.logger import get_logger
    
    logger = get_logger(__name__)
    registry = get_tool_registry()
    backend = get_ollama_backend()
    
    # Core tools (working)
    try:
        registry.register_tool(FileOpsTool())
        logger.info("Registered FileOpsTool")
    except Exception as e:
        logger.warning(f"Failed to register FileOpsTool: {e}")
    
    try:
        registry.register_tool(SandboxExecTool())
        logger.info("Registered SandboxExecTool")
    except Exception as e:
        logger.warning(f"Failed to register SandboxExecTool: {e}")
    
    try:
        registry.register_tool(SpreadsheetOpsTool())
        logger.info("Registered SpreadsheetOpsTool")
    except Exception as e:
        logger.warning(f"Failed to register SpreadsheetOpsTool: {e}")
    
    try:
        registry.register_tool(DocGenTool())
        logger.info("Registered DocGenTool")
    except Exception as e:
        logger.warning(f"Failed to register DocGenTool: {e}")
    
    # Vision tools (need backend, may have architecture issues)
    try:
        registry.register_tool(VisionPipelineTool(backend))
        logger.info("Registered VisionPipelineTool")
    except Exception as e:
        logger.warning(f"Failed to register VisionPipelineTool: {e}")
    
    try:
        registry.register_tool(TiledVisionTool(backend))
        logger.info("Registered TiledVisionTool")
    except Exception as e:
        logger.warning(f"Failed to register TiledVisionTool: {e}")
    
    try:
        registry.register_tool(PDFProcessorTool(backend))
        logger.info("Registered PDFProcessorTool")
    except Exception as e:
        logger.warning(f"Failed to register PDFProcessorTool: {e}")
    
    try:
        registry.register_tool(DocumentSplitterTool())
        logger.info("Registered DocumentSplitterTool")
    except Exception as e:
        logger.warning(f"Failed to register DocumentSplitterTool: {e}")
    
    # Document processor (comprehensive file type support)
    try:
        registry.register_tool(DocumentProcessorTool())
        logger.info("Registered DocumentProcessorTool")
    except Exception as e:
        logger.warning(f"Failed to register DocumentProcessorTool: {e}")
    
    # RAG tools
    try:
        registry.register_tool(LocalRAGTool(backend))
        logger.info("Registered LocalRAGTool")
    except Exception as e:
        logger.warning(f"Failed to register LocalRAGTool: {e}")
    
    try:
        registry.register_tool(SemanticSearchTool(backend))
        logger.info("Registered SemanticSearchTool")
    except Exception as e:
        logger.warning(f"Failed to register SemanticSearchTool: {e}")
    
    try:
        registry.register_tool(KBStatsTool())
        logger.info("Registered KBStatsTool")
    except Exception as e:
        logger.warning(f"Failed to register KBStatsTool: {e}")
    
    try:
        registry.register_tool(KBDeleteTool())
        logger.info("Registered KBDeleteTool")
    except Exception as e:
        logger.warning(f"Failed to register KBDeleteTool: {e}")
    
    # Geospatial tools
    try:
        registry.register_tool(GeospatialCoordinateTool())
        logger.info("Registered GeospatialCoordinateTool")
    except Exception as e:
        logger.warning(f"Failed to register GeospatialCoordinateTool: {e}")
    
    try:
        registry.register_tool(FacilityMapTool())
        logger.info("Registered FacilityMapTool")
    except Exception as e:
        logger.warning(f"Failed to register FacilityMapTool: {e}")
    
    try:
        registry.register_tool(PIDOverlayTool())
        logger.info("Registered PIDOverlayTool")
    except Exception as e:
        logger.warning(f"Failed to register PIDOverlayTool: {e}")
    
    try:
        registry.register_tool(SafetyZoneTool())
        logger.info("Registered SafetyZoneTool")
    except Exception as e:
        logger.warning(f"Failed to register SafetyZoneTool: {e}")
    
    try:
        registry.register_tool(GodsEyeViewTool())
        logger.info("Registered GodsEyeViewTool")
    except Exception as e:
        logger.warning(f"Failed to register GodsEyeViewTool: {e}")
    
    # Log summary
    tools = registry.list_tools()
    logger.info(f"Tool registration complete: {len(tools)} tools registered")
    
    return registry


__all__ = [
    "Tool",
    "ToolExecutionError",
    "ToolValidationError",
    "ToolRegistry",
    "get_tool_registry",
    "register_default_tools",
    "FileOpsTool",
    "SandboxExecTool",
    "SpreadsheetOpsTool",
    "DocGenTool",
    "VisionPipelineTool",
    "TiledVisionTool",
    "PDFProcessorTool",
    "DocumentSplitterTool",
    "DocumentProcessorTool",
    "LocalRAGTool",
    "SemanticSearchTool",
    "KBStatsTool",
    "KBDeleteTool",
    "GeospatialCoordinateTool",
    "FacilityMapTool",
    "PIDOverlayTool",
    "SafetyZoneTool",
    "GodsEyeViewTool",
]
