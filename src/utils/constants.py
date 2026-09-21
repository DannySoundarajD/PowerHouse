"""
Constants and configuration values for Sentinel AI Workbench.
"""

import os
from pathlib import Path
from typing import Final

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, use system environment variables only
    pass

# ============================================================================
# Version
# ============================================================================
VERSION: Final[str] = "1.0.0"
APP_NAME: Final[str] = "Sentinel AI Workbench"

# ============================================================================
# Paths
# ============================================================================
ROOT_DIR: Final[Path] = Path(__file__).parent.parent.parent
SRC_DIR: Final[Path] = ROOT_DIR / "src"
DATA_DIR: Final[Path] = ROOT_DIR / "data"
LOGS_DIR: Final[Path] = ROOT_DIR / "logs"
OUTPUT_DIR: Final[Path] = ROOT_DIR / "output"
KB_DIR: Final[Path] = ROOT_DIR / "kb"
MODELS_DIR: Final[Path] = ROOT_DIR / "models"
CONFIG_DIR: Final[Path] = ROOT_DIR / "config"
DOCKER_DIR: Final[Path] = ROOT_DIR / "docker"

# Ensure directories exist
for directory in [DATA_DIR, LOGS_DIR, OUTPUT_DIR, KB_DIR, MODELS_DIR, CONFIG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Ollama Configuration
# ============================================================================
OLLAMA_HOST: Final[str] = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MAX_LOADED_MODELS: Final[int] = int(os.getenv("OLLAMA_MAX_LOADED_MODELS", "2"))
OLLAMA_NUM_PARALLEL: Final[int] = int(os.getenv("OLLAMA_NUM_PARALLEL", "1"))

# ============================================================================
# Model Configuration
# ============================================================================
DEFAULT_ROUTER_MODEL: Final[str] = os.getenv("SENTINEL_ROUTER_MODEL", "qwen3.5:2b")

# Context management (Sentinel-style)
PROTECT_FIRST_N: Final[int] = int(os.getenv("SENTINEL_PROTECT_FIRST_N", "3"))
PROTECT_LAST_N: Final[int] = int(os.getenv("SENTINEL_PROTECT_LAST_N", "6"))
COMPRESSION_THRESHOLD: Final[float] = float(os.getenv("SENTINEL_COMPRESSION_THRESHOLD", "0.75"))

# Model context windows (tokens)
ROUTER_CONTEXT_WINDOW: Final[int] = 4096
SPECIALIST_CONTEXT_WINDOW: Final[int] = 8192

# ============================================================================
# Database Configuration
# ============================================================================
DB_PATH: Final[Path] = Path(os.getenv("SENTINEL_DB_PATH", str(DATA_DIR / "sessions.db")))
DB_WAL_MODE: Final[bool] = os.getenv("SENTINEL_DB_WAL_MODE", "true").lower() == "true"

# ============================================================================
# Vector Store Configuration
# ============================================================================
CHROMA_PATH: Final[Path] = Path(os.getenv("SENTINEL_CHROMA_PATH", str(DATA_DIR / "chromadb")))
EMBEDDING_MODEL: Final[str] = os.getenv("SENTINEL_EMBEDDING_MODEL", "nomic-embed-text")
RAG_TOP_K: Final[int] = 5
RAG_CHUNK_SIZE: Final[int] = 500
RAG_CHUNK_OVERLAP: Final[int] = 50

# ============================================================================
# Sandbox Configuration
# ============================================================================
SANDBOX_MEMORY_LIMIT: Final[str] = os.getenv("SENTINEL_SANDBOX_MEMORY_LIMIT", "2g")
SANDBOX_CPU_LIMIT: Final[float] = float(os.getenv("SENTINEL_SANDBOX_CPU_LIMIT", "1.5"))
SANDBOX_TIMEOUT: Final[int] = int(os.getenv("SENTINEL_SANDBOX_TIMEOUT", "60"))
SANDBOX_NETWORK_MODE: Final[str] = "none"  # Always air-gapped

# ============================================================================
# Network Guard Configuration
# ============================================================================
NETWORK_MONITOR_ENABLED: Final[bool] = (
    os.getenv("SENTINEL_NETWORK_MONITOR_ENABLED", "true").lower() == "true"
)
LOOPBACK_ONLY: Final[bool] = os.getenv("SENTINEL_LOOPBACK_ONLY", "true").lower() == "true"
NETCHECK_DURATION: Final[int] = 10  # seconds

# ============================================================================
# Logging Configuration
# ============================================================================
LOG_LEVEL: Final[str] = os.getenv("SENTINEL_LOG_LEVEL", "INFO")
LOG_FORMAT: Final[str] = os.getenv("SENTINEL_LOG_FORMAT", "json")

# ============================================================================
# Agent Configuration
# ============================================================================
MAX_TOOL_CALLS_PER_SUBTASK: Final[int] = 10
MAX_SUBTASKS_PER_REQUEST: Final[int] = 5
AGENT_TIMEOUT: Final[int] = 300  # 5 minutes per request

# ============================================================================
# File Access Configuration
# ============================================================================
# Allow access to user-specified directories (comma-separated paths)
# Example: SENTINEL_USER_DIRS="D:\Study Material,C:\Projects"
USER_ACCESSIBLE_DIRS_ENV = os.getenv("SENTINEL_USER_DIRS", "")
USER_ACCESSIBLE_DIRS: list[Path] = [
    Path(p.strip()) for p in USER_ACCESSIBLE_DIRS_ENV.split(",") if p.strip()
]

# ============================================================================
# UI Configuration
# ============================================================================
CLI_PROMPT: Final[str] = "> "
CLI_WELCOME_MESSAGE: Final[str] = f"""
{APP_NAME} v{VERSION}
Sovereign On-Premise AI — Air-Gapped & Secure
Type /help for commands
"""

# ============================================================================
# File Extensions
# ============================================================================
SUPPORTED_DOCUMENT_FORMATS: Final[tuple] = (
    ".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx"
)
SUPPORTED_IMAGE_FORMATS: Final[tuple] = (
    ".png", ".jpg", ".jpeg", ".tiff", ".bmp"
)
SUPPORTED_CODE_EXTENSIONS: Final[tuple] = (
    ".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs"
)

# ============================================================================
# Vision/Image Configuration
# ============================================================================
WORKSPACE_DIR: Final[Path] = ROOT_DIR  # Allow images in workspace
ALLOWED_IMAGE_DIRS: Final[list] = [
    str(WORKSPACE_DIR.resolve()),
    str(OUTPUT_DIR.resolve()),
    str(KB_DIR.resolve())
]
MAX_IMAGE_SIZE_MB: Final[int] = int(os.getenv("SENTINEL_MAX_IMAGE_SIZE_MB", "50"))  # 50MB default
DEFAULT_VISION_MODEL: Final[str] = "qwen3-vl:4b"

# ============================================================================
# Model Roles
# ============================================================================
MODEL_ROLES: Final[tuple] = ("router", "coding", "reasoning", "vision", "embedding", "general")

# ============================================================================
# Task Types
# ============================================================================
TASK_TYPES: Final[tuple] = (
    "coding",
    "reasoning",
    "vision",
    "drafting",
    "retrieval",
    "general",
)
